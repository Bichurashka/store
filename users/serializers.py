from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from users.models import CustomUser


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class CustomUserShowSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = CustomUser
        fields = ["name", "username", "email", "last_login", "groups"]


class CustomUserCreationSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(style={"input_type": "password"}, write_only=True)
    password2 = serializers.CharField(style={"input_type": "password"}, write_only=True)
    admin = serializers.BooleanField(write_only=True, required=False, default=False)
    groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ["name", "username", "email", "password1", "password2", "phone", "admin", "groups"]

    def run_validation(self, data: dict = empty) -> dict:
        errors = {}
        value = {}
        try:
            value = self.to_internal_value(data)
        except ValidationError as e:
            errors.update(e.detail)

        try:
            value = self.validate(data if not value else value)
        except ValidationError as e:
            errors.update(e.detail)

        if errors:
            raise ValidationError(errors)

        return value

    def validate_phone(self, value: str) -> str:
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("Phone number must be 11 digits")
        return value

    def validate(self, attrs: dict) -> dict:
        errors = {}
        password_errors = []
        if attrs["password1"] != attrs["password2"]:
            password_errors.append("Passwords didn't match!")

        temp_user = CustomUser(
            username=attrs.get("username"),
            email=attrs.get("email"),
            name=attrs.get("name"),
            phone=attrs.get("phone"),
        )

        try:
            validate_password(attrs["password2"], user=temp_user)
        except DjangoValidationError as e:
            password_errors.extend(e.messages)

        if password_errors:
            errors["password"] = password_errors

        if errors:
            raise ValidationError(errors)

        return attrs

    def create(self, validated_data: dict) -> CustomUser:
        user: CustomUser = CustomUser.objects.create_user(
            name=validated_data["name"],
            username=validated_data["username"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password2"],
        )
        if "admin" in validated_data and validated_data["admin"]:
            user.groups.add(Group.objects.get(name="admins"))
            user.is_staff = True
            user.save()
        else:
            user.groups.add(Group.objects.get(name="clients"))
        return user
