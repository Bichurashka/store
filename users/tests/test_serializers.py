from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from users.serializers import CustomUserCreationSerializer


class CustomUserCreationSerializerTests(TestCase):
    def setUp(self) -> None:
        self.admin_group = Group.objects.get(name="admins")
        self.clients_group = Group.objects.get(name="clients")

        self.valid_data = {
            "username": "testuser",
            "name": "testuser",
            "email": "testuser@mail.ru",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "phone": "12345678901",
            "admin": False,
        }

    def test_valid_data(self) -> None:
        serializer = CustomUserCreationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_validate_phone_non_digit(self) -> None:
        serializer = CustomUserCreationSerializer()
        with self.assertRaises(ValidationError) as e:
            serializer.validate_phone("testtesttes")
            self.assertIn("Phone number must be 11 digits", str(e.exception))

    def test_validate_phone_wrong_length(self) -> None:
        serializer = CustomUserCreationSerializer()
        with self.assertRaises(ValidationError) as e:
            serializer.validate_phone("0")
            self.assertIn("Phone number must be 11 digits", str(e.exception))

    def test_validate_passwords_do_not_match(self) -> None:
        data = self.valid_data.copy()
        data["password2"] = "DifferentPass!"
        serializer = CustomUserCreationSerializer()
        with self.assertRaises(ValidationError) as e:
            serializer.validate(data)
            self.assertIn("Passwords didn't match!", str(e.exception))

    def test_validate_password_too_short(self) -> None:
        data = self.valid_data.copy()
        data["password1"] = data["password2"] = "a"
        serializer = CustomUserCreationSerializer()
        with self.assertRaises(ValidationError) as e:
            serializer.validate(data)
            self.assertIn(
                "This password is too short. It must contain at least 3 characters.",
                str(e.exception),
            )

    def test_run_validation_field_error(self) -> None:
        data = self.valid_data.copy()
        serializer = CustomUserCreationSerializer()
        data["phone"] = "a"
        with self.assertRaises(ValidationError) as e:
            serializer.run_validation(data)
            self.assertIn("Phone number must be 11 digits", str(e.exception))

    def test_run_validation_validate_error(self) -> None:
        data = self.valid_data.copy()
        serializer = CustomUserCreationSerializer()
        data["password2"] = "a"
        with self.assertRaises(ValidationError) as e:
            serializer.run_validation(data)
            self.assertIn("Passwords didn't match!", str(e.exception))

    def test_run_validation_accumulate_errors(self) -> None:
        data = self.valid_data.copy()
        serializer = CustomUserCreationSerializer()
        data["phone"] = "a"
        data["password2"] = "a"
        with self.assertRaises(ValidationError) as e:
            serializer.run_validation(data)
            self.assertIn("Phone number must be 11 digits", str(e.exception))
            self.assertIn("Passwords didn't match!", str(e.exception))

    def test_create_user_as_client(self) -> None:
        serializer = CustomUserCreationSerializer()
        user = serializer.create(self.valid_data)
        self.assertFalse(user.is_staff)
        self.assertIn(self.clients_group, user.groups.all())

    def test_create_user_as_admin(self) -> None:
        data = self.valid_data.copy()
        data["admin"] = True
        serializer = CustomUserCreationSerializer()
        user = serializer.create(data)
        self.assertTrue(user.is_staff)
        self.assertIn(self.admin_group, user.groups.all())
