from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.db import models

# Create your models here.


class CustomUser(AbstractBaseUser, PermissionsMixin):
    name: models.CharField = models.CharField(max_length=50)
    username: models.CharField = models.CharField(max_length=30, unique=True)
    email: models.EmailField = models.EmailField(max_length=50, unique=True)
    phone: models.CharField = models.CharField(max_length=11, unique=True)
    balance: models.DecimalField = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_active: models.BooleanField = models.BooleanField(default=True)
    is_staff: models.BooleanField = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "name", "phone"]

    objects = UserManager()
