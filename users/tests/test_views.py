from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from users.models import CustomUser


class UserRegistrationViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.valid_data = {
            "name": "test",
            "email": "test@mail.ru",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "username": "test",
            "phone": "12345678901",
        }

    def test_user_registration_view_valid_data(self) -> None:
        response = self.client.post(reverse("registration"), data=self.valid_data)
        self.assertRedirects(response, reverse("health_check"))
        self.assertTrue(CustomUser.objects.filter(username="test").exists())
        self.assertIsNotNone(self.client.session.get("_auth_user_id"))

    def test_user_registration_view_invalid_data(self) -> None:
        data = self.valid_data.copy()
        data["password1"] = "<PASSWORD>"
        response = self.client.post(reverse("registration"), data=data)
        self.assertTemplateUsed(response, "registration.html")
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(CustomUser.objects.filter(username="test").exists())

    def test_user_registration_view_get_request(self) -> None:
        response = self.client.get(reverse("registration"))
        self.assertTemplateUsed(response, "registration.html")


class UserLoginViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.valid_data = {"password": "StrongPassword123!", "username": "test"}
        self.test_user = CustomUser.objects.create_user(**self.valid_data)

    def test_user_login_view_valid_data(self) -> None:
        response = self.client.post(reverse("login"), data=self.valid_data)
        self.assertRedirects(response, reverse("health_check"))
        self.assertEqual(str(self.test_user.pk), self.client.session.get("_auth_user_id"))

    def test_user_login_view_invalid_data(self) -> None:
        data = self.valid_data.copy()
        data["password"] = "<PASSWORD>"
        response = self.client.post(reverse("login"), data=data)
        self.assertTemplateUsed(response, "login.html")
        self.assertTrue(response.context["form"].errors)

    def test_user_login_view_get_request(self) -> None:
        response = self.client.get(reverse("login"))
        self.assertTemplateUsed(response, "login.html")


class UserMeViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = CustomUser.objects.create_user(username="test", password="StrongPassword123!")
        self.client.login(username="test", password="StrongPassword123!")

    def test_user_me_view_valid_data(self) -> None:
        response = self.client.get(reverse("me"))
        self.assertTemplateUsed(response, "me.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context["user"]), str(self.user))


class UserCreateViewTests(TestCase):
    def setUp(self) -> None:
        self.clients_group, _ = Group.objects.get_or_create(name="clients")
        self.admins_group, _ = Group.objects.get_or_create(name="admins")
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username="admin",
            email="admin@mail.ru",
            password="StrongPassword123!",
            name="admin",
            phone="12345678901",
            is_staff=True,
        )
        self.user = CustomUser.objects.create_user(
            username="user",
            email="user@mail.ru",
            password="StrongPassword123!",
            name="user",
            phone="12345678902",
            is_staff=False,
        )
        self.admin.is_staff = True
        self.admin.save()
        self.test_admin = {
            "username": "test_admin",
            "email": "test_admin@mail.ru",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "name": "test_admin",
            "phone": "12345678903",
            "admin_group": "on",
        }
        self.test_user = {
            "username": "test_user",
            "email": "test_user@mail.ru",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
            "name": "test_user",
            "phone": "12345678904",
        }

    def test_user_create_view_valid_user(self) -> None:
        self.client.login(username="admin", password="StrongPassword123!")
        response = self.client.post(reverse("create"), data=self.test_user)
        self.assertEqual(response.status_code, 200)
        user = CustomUser.objects.get(username="test_user")
        self.assertFalse(user.is_staff)
        self.assertIn(self.clients_group, user.groups.all())

    def test_user_create_view_valid_admin(self) -> None:
        self.client.login(username="admin", password="StrongPassword123!")
        response = self.client.post(reverse("create"), data=self.test_admin)
        self.assertEqual(response.status_code, 200)
        user = CustomUser.objects.get(username="test_admin")
        self.assertTrue(user.is_staff)
        self.assertIn(self.admins_group, user.groups.all())

    def test_user_create_view_non_staff(self) -> None:
        self.client.login(username="user", password="StrongPassword123!")
        response = self.client.post(reverse("create"), data=self.test_user)
        self.assertEqual(response.status_code, 302)

    def test_user_create_view_invalid_data(self) -> None:
        self.client.login(username="admin", password="StrongPassword123!")
        data = self.test_user.copy()
        data["password1"] = "<PASSWORD>"
        response = self.client.post(reverse("create"), data=data)
        self.assertTemplateUsed(response, "create.html")
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(CustomUser.objects.filter(username="test_user").exists())

    def test_user_create_view_get_request_data(self) -> None:
        self.client.login(username="admin", password="StrongPassword123!")
        response = self.client.get(reverse("create"))
        self.assertTemplateUsed(response, "create.html")
