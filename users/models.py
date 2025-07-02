from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

# Create your models here.


class CustomUser(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=50)
    login = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=30)  # TODO
    email = models.EmailField(max_length=50, unique=True)
    phone = models.CharField(max_length=11, unique=True)
    balance = models.DecimalField(decimal_places=2, max_digits=10)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "login"
