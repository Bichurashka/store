from django.urls import path

from users.views import create_view, login_view, me_view, registration_view

urlpatterns = [
    path("registration/", registration_view, name="registration"),
    path("login/", login_view, name="login"),
    path("me/", me_view, name="me"),
    path("create/", create_view, name="create"),
]
