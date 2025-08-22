from django.test import TestCase

from users.forms import RegistrationForm


class RegistrationFormTests(TestCase):
    def setUp(self) -> None:
        self.valid_data = {
            "username": "testuser",
            "name": "testuser",
            "email": "testuser@mail.ru",
            "password1": "StrongPass!123",
            "password2": "StrongPass!123",
            "phone": "12345678901",
        }

    def test_valid_data(self) -> None:
        form = RegistrationForm(self.valid_data)
        self.assertTrue(form.is_valid())

    def test_phone_invalid_not_digit(self) -> None:
        data = self.valid_data.copy()
        data["phone"] = "testtesttes"
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_phone_invalid_wrong_length(self) -> None:
        data = self.valid_data.copy()
        data["phone"] = "0"
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
