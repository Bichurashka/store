from datetime import timedelta
from unittest import mock

from django.db import IntegrityError
from django.db.models import QuerySet
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from goods.models import Category, Discounts, Items, OrderItems, Orders
from goods.serializers import CategorySerializer
from goods.tasks import recalculate_items_price
from users.models import CustomUser


def create_category_tree(width: int) -> Category:
    root = Category.objects.create(name="root")
    for i in range(width):
        child = Category.objects.create(name=f"c{i}", parent=root)
        for j in range(width):
            Category.objects.create(name=f"c{i}-{j}", parent=child)
    return root


class CategoryTreeQueriesTests(TestCase):
    def test_tree_serialization_uses_single_query(self) -> None:
        root = create_category_tree(4)
        with self.assertNumQueries(1):
            data = CategorySerializer(root).data
        self.assertEqual(len(data["children"]), 4)
        self.assertEqual(len(data["children"][0]["children"]), 4)

    def test_index_view_queries_do_not_grow_with_categories(self) -> None:
        create_category_tree(5)
        Items.objects.create(name="item", sku="1", base_price=10, price=10)
        # categories + products count + products page
        with self.assertNumQueries(3):
            response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["categories"]), 1)
        root_id = Category.objects.get(name="root").pk
        self.assertEqual(response.context["categories"][0]["id"], root_id)


class OrdersQueriesTests(TestCase):
    def setUp(self) -> None:
        self.user = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )
        self.client_test = APIClient()
        self.client_test.force_authenticate(user=self.user)
        for status in ("Pending", "Shipped", "Paid"):
            order = Orders.objects.create(user=self.user, status=status, price=0)
            for i in range(3):
                item = Items.objects.create(
                    name=f"{status}{i}", sku=f"{status}{i}", base_price=10, price=10
                )
                OrderItems.objects.create(order=order, item=item, amount=1)

    def test_orders_list_queries_do_not_grow_with_items(self) -> None:
        # orders + order items + items
        with self.assertNumQueries(3):
            response = self.client_test.get(reverse("orders"))
        self.assertEqual(len(response.json()["data"]), 3)
        self.assertEqual(len(response.json()["data"][0]["items"]), 3)

    def test_orders_list_invalid_offset_keeps_limit(self) -> None:
        response = self.client_test.get(reverse("orders"), {"limit": 1, "offset": "abc"})
        self.assertEqual([o["status"] for o in response.json()["data"]], ["Pending"])

    def test_concurrent_pending_order_creation_returns_400(self) -> None:
        # simulate a race: the pending order is created after the exists() check
        with mock.patch.object(QuerySet, "exists", return_value=False):
            response = self.client_test.post(reverse("orders"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["data"]["details"], "You already have a pending order")
        self.assertEqual(Orders.objects.filter(user=self.user, status="Pending").count(), 1)

    def test_cached_order_price_is_refreshed(self) -> None:
        order_item = OrderItems.objects.select_related("order").get(
            order__status="Pending", item__name="Pending0"
        )
        order_item.amount = 5
        order_item.save()
        self.assertEqual(order_item.order.price, 70)

    def test_order_items_integrity_error_for_deleted_item_returns_404(self) -> None:
        # The item passes the first existence check, is deleted concurrently, and the deferred
        # FK check fails on commit; after that the item no longer exists.
        missing_item_id = 999999
        exists_calls = iter([True])
        original_exists = QuerySet.exists

        def exists(qs: QuerySet) -> bool:
            if qs.model is Items:
                return next(exists_calls, False)
            return original_exists(qs)

        save = "goods.serializers.OrderItemsCreationSerializer.save"
        with (
            mock.patch.object(QuerySet, "exists", exists),
            mock.patch(save, side_effect=IntegrityError("deferred FK violation")),
        ):
            response = self.client_test.post(
                reverse("order_items"), {"item": missing_item_id, "amount": 1}
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item not found")

    def test_order_items_other_integrity_error_is_not_hidden(self) -> None:
        item = Items.objects.get(name="Pending0")
        save = "goods.serializers.OrderItemsCreationSerializer.save"
        with mock.patch(save, side_effect=IntegrityError("other")):
            with self.assertRaises(IntegrityError):
                self.client_test.post(reverse("order_items"), {"item": item.pk, "amount": 1})

    def test_order_items_update_queries(self) -> None:
        item = Items.objects.get(name="Pending0")
        # item exists + savepoint + pending order + order item FOR UPDATE + update amount
        # + recalculate order price + release savepoint
        with self.assertNumQueries(7):
            response = self.client_test.post(reverse("order_items"), {"item": item.pk, "amount": 1})
        self.assertEqual(response.status_code, 200)

    def test_prices_are_numbers(self) -> None:
        order = self.client_test.get(reverse("orders")).json()["data"][0]
        self.assertEqual(order["price"], 30)
        self.assertEqual(order["items"][0]["item"]["price"], 10)

    def test_orders_list_pagination(self) -> None:
        response = self.client_test.get(reverse("orders"), {"limit": 2, "offset": 1})
        self.assertEqual([o["status"] for o in response.json()["data"]], ["Shipped", "Paid"])

    def test_order_price_recalculated(self) -> None:
        order = Orders.objects.get(user=self.user, status="Pending")
        self.assertEqual(order.price, 30)
        OrderItems.objects.filter(order=order).first().delete()  # type: ignore[union-attr]
        order.refresh_from_db()
        self.assertEqual(order.price, 20)


class ItemsPaginationTests(TestCase):
    def test_items_limit_offset(self) -> None:
        user = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )
        items = [
            Items.objects.create(name=f"i{i}", sku=str(i), base_price=1, price=1) for i in range(5)
        ]
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(reverse("items"), {"limit": 2, "offset": 2})
        self.assertEqual([i["id"] for i in response.json()["data"]], [items[2].pk, items[3].pk])
        response = client.get(reverse("items"))
        self.assertEqual(len(response.json()["data"]), 5)


class RecalculateItemsPriceTests(TestCase):
    def setUp(self) -> None:
        now = timezone.now()
        self.period = {
            "start_datetime": now - timedelta(days=1),
            "end_datetime": now + timedelta(days=1),
        }

    def test_fixed_discount_from_model_choices(self) -> None:
        category = Category.objects.create(name="cat")
        item = Items.objects.create(
            name="item", sku="1", base_price=100, price=100, category=category
        )
        Discounts.objects.create(
            category=category, type=Discounts.DiscountType.FIXED, amount=20, **self.period
        )
        recalculate_items_price()
        item.refresh_from_db()
        self.assertEqual(item.price, 80)

    def test_queries_do_not_grow_with_category_depth(self) -> None:
        parent = None
        for i in range(5):
            parent = Category.objects.create(name=f"lvl{i}", parent=parent)
        Discounts.objects.create(
            category=Category.objects.get(name="lvl0"),
            type=Discounts.DiscountType.PERCENTAGE,
            amount=10,
            **self.period,
        )
        for i in range(10):
            Items.objects.create(
                name=f"i{i}", sku=str(i), base_price=100, price=100, category=parent
            )
        # discounts + categories + items + bulk update
        with self.assertNumQueries(4):
            recalculate_items_price()
        self.assertEqual(set(Items.objects.values_list("price", flat=True)), {90})
