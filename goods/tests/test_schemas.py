from django.test import TestCase

from goods.schemas import CategoryFields, CategoryFilters


class SchemasTests(TestCase):
    def setUp(self) -> None:
        self.valid_data = [CategoryFilters.ID, CategoryFilters.NAME]

    def test_valid_data(self) -> None:
        category_fields = CategoryFields(category_fields=self.valid_data)
        self.assertEqual(category_fields.category_fields, self.valid_data)
