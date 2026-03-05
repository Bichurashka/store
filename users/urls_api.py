from django.urls import path

from users.views_api import CreateUserView, me_view

urlpatterns = [
    path("me/", me_view, name="me_api"),
    path("create/", CreateUserView.as_view(), name="create_api"),
]
