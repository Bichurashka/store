from typing import Any, Dict

from django.db.models import Q, QuerySet
from pydantic import ValidationError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.serializers import Serializer

from goods.models import Category, Items, OrderItems, Orders
from goods.schemas import CategoryFields, ItemsFields
from goods.serializers import (
    CategoryCreationSerializer,
    CategoryPUTSerializer,
    CategorySerializer,
    ItemsCreationSerializer,
    ItemsPUTSerializer,
    ItemsSerializer,
    OrderCreationSerializer,
    OrderSerializer,
)


class CategoryServices:
    def search_category(
        self, search_fields: CategoryFields, search_data: str, sort_type: str = "id"
    ) -> QuerySet:
        allowed_sorts = [f.name for f in Category._meta.get_fields() if not f.is_relation]
        allowed_sorts = allowed_sorts + [f"-{el}" for el in allowed_sorts]
        if sort_type not in allowed_sorts:
            sort_type = "id"

        q = Q()
        for field in search_fields.category_fields:
            q |= Q(**{f"{field}__icontains": search_data})

        return Category.objects.filter(q).order_by(sort_type)


def get_data_from_serializer_categories(serializer: Serializer) -> Dict[str, Any]:
    data: Dict[str, Any] = serializer.validated_data.copy()
    parent = serializer.validated_data.get("parent")
    data["parent"] = parent.pk if parent else None
    return data


class CategoryRequestsService:
    def category_get(self, request: Request) -> dict:
        if request.GET.get("search_fields") and request.GET.get("search_data"):
            service = CategoryServices()
            try:
                validated_search_fields = CategoryFields(
                    category_fields=request.GET.getlist("search_fields")
                )
                fields = service.search_category(
                    validated_search_fields,
                    request.GET["search_data"],
                    request.GET.get("sort_type"),
                )
            except ValidationError:
                return {"data": {}, "status": status.HTTP_400_BAD_REQUEST}
            serializer = CategorySerializer(fields, many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}
        else:
            cat = Category.objects.filter(parent=None).order_by("id")
            serializer = CategorySerializer(cat, many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}

    def category_post(self, request: Request) -> dict:
        serializer = CategoryCreationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            data = get_data_from_serializer_categories(serializer)
            return {"data": data, "status": status.HTTP_201_CREATED}
        return {"data": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}

    def category_put(self, request: Request) -> dict:
        cat_id = request.data.get("id")
        if cat_id:
            try:
                category = Category.objects.get(id=cat_id)
            except Category.DoesNotExist:
                return {
                    "data": {"details": "Category not found"},
                    "status": status.HTTP_404_NOT_FOUND,
                }
            else:
                serializer = CategoryPUTSerializer(
                    instance=category, data=request.data, partial=False
                )
                if serializer.is_valid():
                    serializer.save()
                    data = get_data_from_serializer_categories(serializer)
                    return {"data": data, "status": status.HTTP_200_OK}
                return {"data": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}
        return {"data": {"details": "Category not found"}, "status": status.HTTP_404_NOT_FOUND}


class ItemsServices:
    def search_items(
        self, search_fields: ItemsFields, search_data: str, sort_type: str = "id"
    ) -> QuerySet:
        allowed_sorts = [f.name for f in Items._meta.get_fields() if not f.is_relation]
        allowed_sorts = allowed_sorts + [f"-{el}" for el in allowed_sorts]
        if sort_type not in allowed_sorts:
            sort_type = "id"

        q = Q()
        for field in search_fields.items_fields:
            q |= Q(**{f"{field}__icontains": search_data})

        return Items.objects.filter(q).order_by(sort_type)


def get_data_from_serializer_items(serializer: Serializer) -> Dict[str, Any]:
    data: Dict[str, Any] = serializer.validated_data.copy()
    category = serializer.validated_data.get("category")
    data["category"] = category.pk if category else None
    description = serializer.validated_data.get("description")
    data["description"] = description if description else None
    return data


class ItemsRequestsServices:
    def items_get(self, request: Request) -> dict:
        if request.GET.get("search_fields") and request.GET.get("search_data"):
            service = ItemsServices()
            try:
                validated_search_fields = ItemsFields(
                    items_fields=request.GET.getlist("search_fields")
                )
                fields = service.search_items(
                    validated_search_fields,
                    request.GET["search_data"],
                    request.GET.get("sort_type"),
                )
            except ValidationError:
                return {"data": {}, "status": status.HTTP_400_BAD_REQUEST}
            serializer = ItemsSerializer(fields, many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}
        else:
            items = Items.objects.all().order_by("id")
            serializer = ItemsSerializer(items, many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}

    def items_post(self, request: Request) -> dict:
        serializer = ItemsCreationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            data = get_data_from_serializer_items(serializer)
            return {"data": data, "status": status.HTTP_201_CREATED}
        return {"data": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}

    def items_put(self, request: Request) -> dict:
        item_id = request.data.get("id")
        if item_id:
            try:
                item = Items.objects.get(id=item_id)
            except Items.DoesNotExist:
                return {"data": {"details": "Item not found"}, "status": status.HTTP_404_NOT_FOUND}
            else:
                serializer = ItemsPUTSerializer(instance=item, data=request.data, partial=False)
                if serializer.is_valid():
                    serializer.save()
                    data = get_data_from_serializer_items(serializer)
                    return {"data": data, "status": status.HTTP_200_OK}
                return {"data": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}
        return {"data": {"details": "Item not found"}, "status": status.HTTP_404_NOT_FOUND}


# Orders


class OrdersServices:
    def orders_get(self, request: Request) -> dict:
        orders = Orders.objects.filter(user_id=request.user.id).order_by("id")
        serializer = OrderSerializer(orders, many=True)
        return {"data": serializer.data, "status": status.HTTP_200_OK}

    def orders_post(self, request: Request) -> dict:
        pending_order = Orders.objects.filter(user_id=request.user.id).filter(status="Pending")
        if pending_order:
            return {
                "data": {"details": "You already have a pending order"},
                "status": status.HTTP_400_BAD_REQUEST,
            }
        data = {"status": "Pending", "price": 0}
        serializer = OrderCreationSerializer(data=data)
        serializer.is_valid()
        serializer.save(user=request.user)
        return {"data": serializer.validated_data, "status": status.HTTP_201_CREATED}

    def get_or_create_order(self, request: Request) -> Orders:
        try:
            order = Orders.objects.filter(user_id=request.user.id).get(status="Pending")
            return order
        except Orders.DoesNotExist:
            data = {"status": "Pending", "price": 0, "user_id": request.user.id}
            return Orders.objects.create(**data)


# OrderItems


class OrderItemsServices:
    def get_or_create_order_items(self, item_id: int, order_id: int) -> OrderItems:
        try:
            order_items = OrderItems.objects.get(item=item_id, order=order_id)
            return order_items
        except OrderItems.DoesNotExist:
            data = {"order_id": order_id, "item_id": item_id, "amount": 0}
            return OrderItems.objects.create(**data)
