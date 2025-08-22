from django.urls import path

from users.views_api import CreateView, me_view

urlpatterns = [
    path("me/", me_view, name="me_api"),
    path("create/", CreateView.as_view(), name="create_api"),
]
