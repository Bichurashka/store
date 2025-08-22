from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import CustomUser


class UserMeAPITests(APITestCase):
    def setUp(self) -> None:
        self.user_test = CustomUser.objects.create_user(
            username="test", email="test@mail.ru", password="StrongPassword123!"
        )
        self.client_test = APIClient()
        self.client_test.force_authenticate(user=self.user_test)

    def test_user_me_api_success(self) -> None:
        response = self.client_test.get(reverse("me_api"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user_test.username)
        self.assertEqual(response.data["email"], self.user_test.email)


class UserCreateAPITests(APITestCase):
    def setUp(self) -> None:
        self.test_admin = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
        )
        self.test_admin.is_staff = True
        self.test_admin.save()

        self.test_user = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
        )

        self.test_client = APIClient()

    def test_user_admin_create_api_success(self) -> None:
        valid_user = {
            "name": "test",
            "email": "test@mail.ru",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "username": "test",
            "phone": "12345678903",
        }
        self.test_client.force_authenticate(user=self.test_admin)
        response = self.test_client.post(reverse("create_api"), data=valid_user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], valid_user["name"])

    def test_user_default_user_create_api_failure(self) -> None:
        valid_user = {
            "name": "test1",
            "email": "test1@mail.ru",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "username": "test1",
            "phone": "12345678904",
        }
        self.test_client.force_authenticate(user=self.test_user)
        response = self.test_client.post(reverse("create_api"), data=valid_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_create_api_invalid_user(self) -> None:
        invalid_user = {
            "name": "test2",
            "email": "test2@mail.ru",
            "password1": "StrongPassword123",
            "password2": "StrongPassword123!",
            "username": "test2",
            "phone": "12345678905",
        }
        self.test_client.force_authenticate(user=self.test_admin)
        response = self.test_client.post(reverse("create_api"), data=invalid_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Passwords didn't match!", str(response.data))
