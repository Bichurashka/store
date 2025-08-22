from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class RegistrationForm(UserCreationForm):
    name = forms.CharField(max_length=50)
    username = forms.CharField(max_length=50)
    email = forms.EmailField(max_length=50)
    phone = forms.CharField(max_length=11)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_phone(self) -> str:
        phone: str = self.cleaned_data.get("phone", "")
        if not phone.isdigit() or len(phone) != 11:
            self.add_error("phone", "Phone number must be 11 digits")
        return phone

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2", "phone", "name")


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", max_length=30)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
