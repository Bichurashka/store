from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from goods.models import Category, Items, OrderItems, Orders
from users.models import CustomUser


class GoodsOneCategoryAPITests(APITestCase):
    def setUp(self) -> None:
        self.admin_test = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
        )
        self.admin_test.is_staff = True
        self.admin_test.save()

        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
        )
        self.client_test = APIClient()

        self.cat = Category.objects.create(name="cat", parent=None)

    def test_not_existing_category(self) -> None:
        url = reverse("one_category", args=[9999])
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # GET tests

    def test_get_success(self) -> None:
        url = reverse("one_category", args=[self.cat.pk])
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("project", response.json())
        self.assertIn("api_version", response.json())
        self.assertIn("data", response.json())
        self.assertEqual(response.json()["data"]["name"], "cat")

    # PATCH tests

    def test_patch_success(self) -> None:
        url = reverse("one_category", args=[self.cat.pk])
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.patch(url, data={"name": "new name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "new name")
        self.assertEqual(response.json()["data"]["parent"], self.cat.parent)

    def test_patch_fail(self) -> None:
        url = reverse("one_category", args=[self.cat.pk])
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.patch(url, data={"parent": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoodsCategoryAPITests(APITestCase):
    def setUp(self) -> None:
        self.admin_test = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
        )
        self.admin_test.is_staff = True
        self.admin_test.save()

        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
        )

        self.parent = Category.objects.create(name="Parent")
        self.child = Category.objects.create(name="Child", parent=self.parent)
        self.child2 = Category.objects.create(name="Child2", parent=self.parent)

        self.client_test = APIClient()

    # GET tests

    def test_get_without_args(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(reverse("category"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("project", response.json())
        self.assertIn("api_version", response.json())
        self.assertIn("data", response.json())

    def test_get_with_args(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("category") + "?search_fields=name&search_data=chi"
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_with_wrong_search_fields(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("category") + "?search_fields=123&search_data=chi"
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_with_wrong_search_data(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("category") + "?search_fields=name&search_data=123"
        response = self.client_test.get(url)
        self.assertEqual(response.json()["data"], [])

    # POST tests

    def test_post_not_admin(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(reverse("category"), data={"name": "cat"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_creation_success(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.post(
            reverse("category"), data={"name": "cat", "parent": self.parent.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cat = Category.objects.get(name="cat")
        self.assertEqual(cat.parent, self.parent)
        self.assertEqual(str(cat), cat.name)

    def test_post_creation_failure(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.post(reverse("category"), data={"name": "cat", "parent": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # PUT tests

    def test_put_without_id(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(reverse("category"), data={"name": "cat"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_with_name(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("category"), data={"id": self.child.pk, "name": "cat"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "cat")
        self.assertEqual(response.json()["data"]["parent"], None)

    def test_put_with_args(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("category"),
            data={"id": self.child.pk, "name": "cat2", "parent": self.child2.pk},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "cat2")
        self.assertEqual(response.json()["data"]["parent"], self.child2.pk)

    def test_put_wrong_args(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("category"), data={"id": self.child.pk, "name": "cat", "parent": 9999}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_not_found(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(reverse("category"), data={"id": 9999, "name": "cat"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_method(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.delete(reverse("category"), data={"name": "Child2"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class GoodsOneItemAPITests(APITestCase):
    def setUp(self) -> None:
        self.admin_test = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
        )
        self.admin_test.is_staff = True
        self.admin_test.save()

        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
        )
        self.client_test = APIClient()

        self.category = Category.objects.create(name="cat")
        self.item = Items.objects.create(
            name="item",
            base_price=100,
            price=100,
            description="123",
            sku="1",
            category=self.category,
        )

    def test_not_existing_item(self) -> None:
        url = reverse("one_item", args=[9999])
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # GET tests

    def test_get_success(self) -> None:
        url = reverse("one_item", args=[self.item.pk])
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "item")

    # PATCH tests

    def test_patch_success(self) -> None:
        url = reverse("one_item", args=[self.item.pk])
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.patch(url, data={"name": "new name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "new name")

    def test_patch_fail(self) -> None:
        url = reverse("one_item", args=[self.item.pk])
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.patch(url, data={"category": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoodsItemsAPITests(APITestCase):
    def setUp(self) -> None:
        self.admin_test = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
        )
        self.admin_test.is_staff = True
        self.admin_test.save()

        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
        )

        self.category = Category.objects.create(name="cat")
        self.item = Items.objects.create(
            name="item",
            base_price=100,
            price=100,
            description="123",
            sku="1",
            category=self.category,
        )

        self.client_test = APIClient()

    # GET tests

    def test_get_without_args(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(reverse("items"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_with_args(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("items") + "?search_fields=name&search_data=it"
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"][0]["name"], "item")

    def test_get_with_wrong_search_fields(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("items") + "?search_fields=123&search_data=it"
        response = self.client_test.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_with_wrong_search_data(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        url = reverse("items") + "?search_fields=name&search_data=123"
        response = self.client_test.get(url)
        self.assertEqual(response.json()["data"], [])

    # POST tests

    def test_post_not_admin(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(
            reverse("items"),
            data={
                "name": "item1",
                "base_price": 100,
                "price": 100,
                "sku": 2,
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_creation_success(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.post(
            reverse("items"),
            data={
                "name": "item2",
                "base_price": 123,
                "price": 123,
                "sku": 2,
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = Items.objects.get(name="item2")
        self.assertEqual(item.name, "item2")
        self.assertEqual(item.sku, "2")

    def test_post_creation_failure(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.post(
            reverse("items"),
            data={"name": "item3", "base_price": 123, "price": 123, "sku": 2, "category": 9999},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # PUT tests

    def test_put_without_id(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(reverse("items"), data={"name": "item"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_with_required_args(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("items"),
            data={"id": self.item.pk, "name": "item1", "base_price": 100, "price": 100, "sku": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "item1")
        self.assertEqual(response.json()["data"]["description"], None)
        self.assertEqual(response.json()["data"]["category"], None)

    def test_put_with_args(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("items"),
            data={
                "id": self.item.pk,
                "name": "item1",
                "base_price": 100,
                "price": 100,
                "sku": 2,
                "description": "321",
                "category": self.category.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "item1")
        self.assertEqual(response.json()["data"]["category"], self.category.pk)

    def test_put_wrong_args(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("items"),
            data={
                "id": self.item.pk,
                "name": "item1",
                "base_price": 100,
                "price": 100,
                "sku": 2,
                "description": "321",
                "category": 9999,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_not_found(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.put(
            reverse("items"),
            data={"id": 9999, "name": "item1", "base_price": 100, "price": 100, "sku": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_method(self) -> None:
        self.client_test.force_authenticate(user=self.admin_test)
        response = self.client_test.delete(reverse("items"), data={"id": self.item.pk})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class GoodsOrdersAPITests(APITestCase):
    def setUp(self) -> None:
        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )
        self.user_test2 = CustomUser.objects.create_user(
            username="user2",
            email="user2@mail.ru",
            password="StrongPassword123!",
            name="user2",
            phone="12345678902",
        )

        self.client_test = APIClient()

    #  GET tests

    def test_get_orders_by_user(self) -> None:
        Orders.objects.create(user=self.user_test, status="Pending", price=100)
        Orders.objects.create(user=self.user_test, status="Shipped", price=100)
        Orders.objects.create(user=self.user_test2, status="Pending", price=100)
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(reverse("orders"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_get_orders_when_empty(self) -> None:
        Orders.objects.create(user=self.user_test, status="Pending", price=100)
        self.client_test.force_authenticate(user=self.user_test2)
        response = self.client_test.get(reverse("orders"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 0)

    #  POST tests

    def test_post_orders_creation_success(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(reverse("orders"))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["status"], "Pending")

    def test_post_orders_creation_fail(self) -> None:
        Orders.objects.create(user=self.user_test, status="Pending", price=100)
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(reverse("orders"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["data"]["details"], "You already have a pending order")


class GoodsOneOrderAPITests(APITestCase):
    def setUp(self) -> None:
        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )

        self.client_test = APIClient()

    def test_get_one_order_exists(self) -> None:
        order = Orders.objects.create(user=self.user_test, status="Pending", price=100)
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(reverse("one_order"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], order.pk)

    def test_get_one_order_does_not_exist(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.get(reverse("one_order"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["price"], "0.00")
        self.assertEqual(response.json()["data"]["status"], "Pending")


class GoodsOrderItemsAPITests(APITestCase):
    def setUp(self) -> None:
        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )
        self.item_test = Items.objects.create(name="item1", sku="sku1", base_price=100, price=100)
        self.client_test = APIClient()

    def test_post_order_items_creation_success(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(
            reverse("order_items"), data={"item": self.item_test.pk, "amount": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Orders.objects.get(user=self.user_test, status="Pending")
        order_item = OrderItems.objects.get(order=order, item=self.item_test)
        self.assertEqual(order_item.amount, 2)

    def test_post_order_items_increasing_amount(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        self.client_test.post(reverse("order_items"), data={"item": self.item_test.pk, "amount": 1})
        response = self.client_test.post(
            reverse("order_items"), data={"item": self.item_test.pk, "amount": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Orders.objects.get(user=self.user_test, status="Pending")
        order_item = OrderItems.objects.get(order=order, item=self.item_test)
        self.assertEqual(order_item.amount, 3)

    def test_post_order_items_decreasing_amount_below_zero(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        self.client_test.post(reverse("order_items"), data={"item": self.item_test.pk, "amount": 1})
        self.client_test.post(
            reverse("order_items"), data={"item": self.item_test.pk, "amount": -5}
        )
        order = Orders.objects.get(user=self.user_test, status="Pending")
        order_item = OrderItems.objects.get(order=order, item=self.item_test)
        self.assertEqual(order_item.amount, 0)

    def test_patch_order_items_success(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        self.client_test.patch(
            reverse("order_items"), data={"item": self.item_test.pk, "amount": 1}
        )
        response = self.client_test.patch(
            reverse("order_items"), data={"item": self.item_test.pk, "amount": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Orders.objects.get(user=self.user_test, status="Pending")
        order_item = OrderItems.objects.get(order=order, item=self.item_test)
        self.assertEqual(order_item.amount, 2)

    def test_order_items_failure_wrong_item(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(reverse("order_items"), data={"item": 9999, "amount": 2})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["detail"], "Item not found")

    def test_order_items_failure_wrong_request(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.post(reverse("order_items"), data={"item": self.item_test.pk})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)


class GoodsOrderItemAPITests(APITestCase):
    def setUp(self) -> None:
        self.user_test = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678901",
        )
        self.item_test = Items.objects.create(name="item1", sku="sku1", base_price=100, price=100)
        self.order_test = Orders.objects.create(user=self.user_test, status="Pending", price=200)
        self.order_item_test = OrderItems.objects.create(
            order=self.order_test, item=self.item_test, amount=2
        )
        self.client_test = APIClient()

    def test_order_item_delete_success(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.delete(reverse("order_item", args=[self.item_test.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_order_item_delete_failure_wrong_item(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        response = self.client_test.delete(reverse("order_item", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_item_delete_failure_no_pending_order(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        self.order_test.status = "Shipped"
        self.order_test.save()
        response = self.client_test.delete(reverse("order_item", args=[self.item_test.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_item_delete_failure_no_item_in_order(self) -> None:
        self.client_test.force_authenticate(user=self.user_test)
        self.order_item_test.delete()
        response = self.client_test.delete(reverse("order_item", args=[self.item_test.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
