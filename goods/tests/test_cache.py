from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from goods.models import Category, Discounts, Items
from goods.tasks import recalculate_items_price
from users.models import CustomUser

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM_CACHE)
class GoodsCacheTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client_api = APIClient()
        self.root = Category.objects.create(name="root")
        Category.objects.create(name="child", parent=self.root)
        self.item = Items.objects.create(
            name="item", sku="1", base_price=100, price=100, category=self.root
        )

    def get_categories(self, **params: str) -> list:
        return list(self.client_api.get(reverse("category"), params).json()["data"])

    def get_items(self, **params: str) -> list:
        return list(self.client_api.get(reverse("items"), params).json()["data"])

    def test_repeated_category_list_is_served_from_cache(self) -> None:
        first = self.get_categories()
        with self.assertNumQueries(0):
            second = self.get_categories()
        self.assertEqual(first, second)
        self.assertEqual(second[0]["children"][0]["name"], "child")

    def test_repeated_items_list_is_served_from_cache(self) -> None:
        first = self.get_items()
        with self.assertNumQueries(0):
            second = self.get_items()
        self.assertEqual(first, second)

    def test_index_category_tree_is_cached(self) -> None:
        self.client.get(reverse("index"))
        # only products count + products page, the tree comes from the cache
        with self.assertNumQueries(2):
            response = self.client.get(reverse("index"))
        self.assertEqual(response.context["categories"][0]["children"][0]["name"], "child")

    def test_category_changes_invalidate_cache(self) -> None:
        self.get_categories()
        self.client.get(reverse("index"))

        Category.objects.create(name="new", parent=self.root)
        names = [c["name"] for c in self.get_categories()[0]["children"]]
        self.assertEqual(names, ["child", "new"])
        tree = self.client.get(reverse("index")).context["categories"]
        self.assertEqual(len(tree[0]["children"]), 2)

        self.root.name = "renamed"
        self.root.save()
        self.assertEqual(self.get_categories()[0]["name"], "renamed")

        Category.objects.get(name="new").delete()
        self.assertEqual(len(self.get_categories()[0]["children"]), 1)

    def test_category_delete_invalidates_items(self) -> None:
        self.assertEqual(self.get_items()[0]["category"], self.root.pk)
        self.root.delete()
        self.assertIsNone(self.get_items()[0]["category"])

    def test_item_changes_invalidate_cache(self) -> None:
        self.get_items()
        Items.objects.create(name="second", sku="2", base_price=10, price=10)
        self.assertEqual(len(self.get_items()), 2)

        self.item.name = "changed"
        self.item.save()
        self.assertEqual(self.get_items()[0]["name"], "changed")

        self.item.delete()
        self.assertEqual([i["name"] for i in self.get_items()], ["second"])

    def test_item_update_through_api_invalidates_cache(self) -> None:
        admin = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
            is_staff=True,
        )
        self.client_api.force_authenticate(user=admin)
        self.get_items()
        response = self.client_api.patch(
            reverse("one_item", args=[self.item.pk]), {"name": "patched"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_items()[0]["name"], "patched")

    def test_price_recalculation_invalidates_items(self) -> None:
        self.assertEqual(self.get_items()[0]["price"], 100)
        now = timezone.now()
        Discounts.objects.create(
            category=self.root,
            type=Discounts.DiscountType.PERCENTAGE,
            amount=10,
            start_datetime=now - timedelta(days=1),
            end_datetime=now + timedelta(days=1),
        )
        recalculate_items_price()
        self.assertEqual(self.get_items()[0]["price"], 90)

    def test_pages_do_not_share_cache_entries(self) -> None:
        Items.objects.create(name="second", sku="2", base_price=10, price=10)
        first_page = self.get_items(limit="1")
        second_page = self.get_items(limit="1", offset="1")
        self.assertEqual([i["name"] for i in first_page], ["item"])
        self.assertEqual([i["name"] for i in second_page], ["second"])
        self.assertEqual(len(self.get_items()), 2)
        # equivalent bounds share one entry
        with self.assertNumQueries(0):
            self.assertEqual(self.get_items(limit="1", offset="bad"), first_page)

    def test_search_is_not_cached(self) -> None:
        params = {"search_fields": "name", "search_data": "ite"}
        self.get_items(**params)
        with self.assertNumQueries(1):
            self.get_items(**params)
