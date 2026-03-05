from django.test import TestCase

from goods.models import Category, Items
from goods.schemas import CategoryFields, CategoryFilters, ItemsFields, ItemsFilters
from goods.services import CategoryServices, ItemsServices


class CategoryServicesTests(TestCase):
    def setUp(self) -> None:
        self.service = CategoryServices()
        self.cat1 = Category.objects.create(name="Cat1")
        self.cat2 = Category.objects.create(name="Cat2")
        self.cat3 = Category.objects.create(name="Cot1")

        self.fields = CategoryFields(category_fields=[CategoryFilters.NAME])

    def test_search_by_name(self) -> None:
        cats = self.service.search_category(self.fields, "Cat", "name")
        self.assertEqual(len(cats), 2)
        names = [cat.name for cat in cats]
        self.assertIn("Cat1", names)
        self.assertIn("Cat2", names)
        self.assertNotIn("Cot1", names)

    def test_sorting_asc(self) -> None:
        cats = self.service.search_category(self.fields, "c", "name")
        names = [cat.name for cat in cats]
        self.assertEqual(names, ["Cat1", "Cat2", "Cot1"])

    def test_sorting_desc(self) -> None:
        cats = self.service.search_category(self.fields, "c", "-name")
        names = [cat.name for cat in cats]
        self.assertEqual(names, ["Cot1", "Cat2", "Cat1"])

    def test_invalid_sorting(self) -> None:
        cats = self.service.search_category(self.fields, "c", "invalid")
        ids = [cat.id for cat in cats]
        self.assertEqual(ids, [self.cat1.pk, self.cat2.pk, self.cat3.pk])

    def test_empty_results(self) -> None:
        cats = self.service.search_category(self.fields, "empty")
        self.assertEqual(len(cats), 0)

    def test_search_multiple_fields(self) -> None:
        fields = CategoryFields(category_fields=[CategoryFilters.ID, CategoryFilters.NAME])
        cats = self.service.search_category(fields, "cat")
        names = [cat.name for cat in cats]
        self.assertIn("Cat1", names)
        self.assertIn("Cat2", names)
        self.assertNotIn("Cot1", names)


class ItemsServicesTests(TestCase):
    def setUp(self) -> None:
        self.service = ItemsServices()
        self.item1 = Items.objects.create(name="Item1", sku="1", base_price=100, price=100)
        self.item2 = Items.objects.create(name="Item2", sku="2", base_price=100, price=100)
        self.item3 = Items.objects.create(name="Itom1", sku="3", base_price=100, price=100)

        self.fields = ItemsFields(items_fields=[ItemsFilters.NAME])

    def test_search_by_name(self) -> None:
        items = self.service.search_items(self.fields, "Item", "name")
        self.assertEqual(len(items), 2)
        names = [it.name for it in items]
        self.assertIn("Item1", names)
        self.assertIn("Item2", names)
        self.assertNotIn("Itom1", names)

    def test_sorting_asc(self) -> None:
        items = self.service.search_items(self.fields, "It", "name")
        names = [it.name for it in items]
        self.assertEqual(names, ["Item1", "Item2", "Itom1"])

    def test_sorting_desc(self) -> None:
        items = self.service.search_items(self.fields, "It", "-name")
        names = [it.name for it in items]
        self.assertEqual(names, ["Itom1", "Item2", "Item1"])

    def test_invalid_sorting(self) -> None:
        items = self.service.search_items(self.fields, "It", "invalid")
        ids = [it.id for it in items]
        self.assertEqual(ids, [self.item1.pk, self.item2.pk, self.item3.pk])

    def test_empty_results(self) -> None:
        items = self.service.search_items(self.fields, "empty")
        self.assertEqual(len(items), 0)

    def test_search_multiple_fields(self) -> None:
        fields = ItemsFields(items_fields=[ItemsFilters.ID, ItemsFilters.NAME])
        items = self.service.search_items(fields, "Item")
        names = [it.name for it in items]
        self.assertIn("Item1", names)
        self.assertIn("Item2", names)
        self.assertNotIn("Itom1", names)
