from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from goods.models import Category, Discounts, Items
from goods.tasks import collect_items_discounts, recalculate_items_price


class GoodsCollectItemsDiscountsTest(TestCase):
    def setUp(self) -> None:
        self.parent_category = Category.objects.create(name="Parent")
        self.child_category = Category.objects.create(name="Child", parent=self.parent_category)
        self.item = Items.objects.create(
            name="Test", base_price=100, price=100, category=self.child_category
        )
        now = timezone.now()
        self.parent_discount = Discounts.objects.create(
            category=self.parent_category,
            type="percentage",
            amount=10,
            start_datetime=now - timedelta(days=1),
            end_datetime=now + timedelta(days=1),
        )
        self.child_discount = Discounts.objects.create(
            category=self.child_category,
            type="fixed",
            amount=10,
            start_datetime=now - timedelta(days=1),
            end_datetime=now + timedelta(days=1),
        )

    def test_collect_discount(self) -> None:
        result = collect_items_discounts()
        self.assertIn(self.item.pk, result)
        discounts = result[self.item.pk]
        self.assertEqual(len(discounts), 2)


class GoodsRecalculateItemsPriceTest(TestCase):
    def setUp(self) -> None:
        self.category = Category.objects.create(name="Cat")
        self.item = Items.objects.create(
            name="Test", base_price=100, price=100, category=self.category
        )
        now = timezone.now()
        Discounts.objects.create(
            category=self.category,
            type="percentage",
            amount=30,
            start_datetime=now - timedelta(days=1),
            end_datetime=now + timedelta(days=1),
        )
        Discounts.objects.create(
            category=self.category,
            type="fixed",
            amount=70,
            start_datetime=now - timedelta(days=1),
            end_datetime=now + timedelta(days=1),
        )

    def test_recalculate_price(self) -> None:
        recalculate_items_price()
        self.item.refresh_from_db()
        self.assertEqual(self.item.price, 35)
