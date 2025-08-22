from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistrationForm


def registration_view(request: WSGIRequest) -> HttpResponse | HttpResponsePermanentRedirect:
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("health_check")
        else:
            return render(request, "registration.html", {"form": form})
    return render(request, "registration.html", {"form": form})


def login_view(request: WSGIRequest) -> HttpResponse | HttpResponsePermanentRedirect:
    form = LoginForm(data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            login(request, user)
            return redirect("health_check")
    return render(request, "login.html", {"form": form})


@login_required
def me_view(request: WSGIRequest) -> HttpResponse:
    return render(request, "me.html")


@staff_member_required
def create_view(request: WSGIRequest) -> HttpResponse:
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save(commit=False)
            if request.POST.get("admin_group") == "on":
                user.is_staff = True
            user.save()
            if request.POST.get("admin_group") == "on":
                user.groups.add(Group.objects.get(name="admins"))
            else:
                user.groups.add(Group.objects.get(name="clients"))
            user.save()
    return render(request, "create.html", {"form": form})
