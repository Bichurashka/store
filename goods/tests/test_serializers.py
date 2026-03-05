from django.test import TestCase

from goods.models import Category, Items
from goods.serializers import CategoryPUTSerializer, CategorySerializer, ItemsPUTSerializer


class CategorySerializationTests(TestCase):
    def setUp(self) -> None:
        self.parent = Category.objects.create(name="Parent")
        self.child = Category.objects.create(name="Child", parent=self.parent)
        self.child2 = Category.objects.create(name="Child2", parent=self.parent)
        self.grandchild = Category.objects.create(name="Grandchild", parent=self.child)

    def test_serialization_with_children(self) -> None:
        serializer = CategorySerializer(self.parent)
        data = serializer.data
        names = [child["name"] for child in data["children"]]
        self.assertEqual(len(names), 2)
        self.assertIn("Child", names)
        self.assertIn("Child2", names)
        grandchild = data["children"][0]["children"][0]["name"]
        self.assertEqual(grandchild, "Grandchild")

    def test_serialization_without_children(self) -> None:
        serializer = CategorySerializer(self.grandchild)
        data = serializer.data
        self.assertIn("children", data)
        self.assertEqual(len(data["children"]), 0)


class CategoryPUTSerializationTests(TestCase):
    def setUp(self) -> None:
        self.parent = Category.objects.create(name="Parent")
        self.child = Category.objects.create(name="Child", parent=self.parent)
        self.new_parent = Category.objects.create(name="NewParent")

    def test_serialization_with_args(self) -> None:
        data = {
            "name": "Child",
            "parent": self.new_parent.pk,
        }
        serializer = CategoryPUTSerializer(instance=self.child, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["name"], data["name"])
        self.assertEqual(serializer.data["parent"], data["parent"])

    def test_serialization_without_args(self) -> None:
        data = {"name": "Child"}
        serializer = CategoryPUTSerializer(instance=self.child, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["parent"], None)

    def test_serialization_with_none_args(self) -> None:
        data = {"name": "Child", "parent": None}
        serializer = CategoryPUTSerializer(instance=self.child, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["parent"], None)


class ItemsPUTSerializationTests(TestCase):
    def setUp(self) -> None:
        self.category = Category.objects.create(name="cat")
        self.category2 = Category.objects.create(name="cat2")
        self.item = Items.objects.create(
            name="item",
            base_price=100,
            price=100,
            description="123",
            sku="1",
            category=self.category,
        )

    def test_serialization_with_args(self) -> None:
        data = {
            "name": "Item1",
            "price": 100,
            "base_price": 100,
            "sku": "1",
            "description": "321",
            "category": self.category2.pk,
        }
        serializer = ItemsPUTSerializer(instance=self.item, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["description"], "321")
        self.assertEqual(serializer.data["category"], self.category2.pk)

    def test_serialization_without_args(self) -> None:
        data = {"name": "Item1", "base_price": 100, "price": 100, "sku": "1"}
        serializer = ItemsPUTSerializer(instance=self.item, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["description"], None)
        self.assertEqual(serializer.data["category"], None)

    def test_serialization_with_none_args(self) -> None:
        data = {
            "name": "Item1",
            "base_price": 100,
            "price": 100,
            "sku": "1",
            "category": None,
            "description": None,
        }
        serializer = ItemsPUTSerializer(instance=self.item, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data["description"], None)
        self.assertEqual(serializer.data["category"], None)
