from typing import Any, cast

from rest_framework import serializers

from goods.models import Category, Items, OrderItems, Orders
from users.models import CustomUser

# Category


class CategoryCreationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "parent"]


class CategoryPUTSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    def update(self, instance: Category, validated_data: dict[str, Any]) -> Category:
        if "parent" not in validated_data:
            instance.parent = None
        return cast(Category, super().update(instance, validated_data))

    class Meta:
        model = Category
        fields = ["id", "name", "parent"]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "children"]

    def get_children(self, obj: Category) -> list[dict[str, Any]]:
        queryset = Category.objects.filter(parent=obj)
        return cast(list[dict[str, Any]], CategorySerializer(queryset, many=True).data)


# Items


class ItemsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Items
        fields = ["id", "name", "price", "description", "sku", "category"]


class ItemsCreationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Items
        fields = ["id", "name", "base_price", "price", "description", "sku", "category"]


class ItemsPUTSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    description = serializers.CharField(required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    def update(self, instance: Items, validated_data: dict[str, Any]) -> Items:
        if "description" not in validated_data:
            instance.description = None
        if "category" not in validated_data:
            instance.category = None
        return cast(Items, super().update(instance, validated_data))

    class Meta:
        model = Items
        fields = "__all__"


# OrderItems


class OrderItemsSerializer(serializers.ModelSerializer):
    item = ItemsSerializer()

    class Meta:
        model = OrderItems
        fields = "__all__"


class OrderItemsCreationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    order = serializers.PrimaryKeyRelatedField(queryset=Orders.objects.all(), required=False)

    class Meta:
        model = OrderItems
        fields = "__all__"


class OrderItemsInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    amount = serializers.IntegerField()


# Orders


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemsSerializer(many=True, read_only=True)

    class Meta:
        model = Orders
        fields = ["id", "price", "status", "items"]


class OrderCreationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = Orders
        fields = "__all__"
