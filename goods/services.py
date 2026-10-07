from typing import Any, Dict

from django.db import IntegrityError, transaction
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

MAX_PAGE_LIMIT = 100


def _allowed_sorts(model: Any) -> frozenset[str]:
    fields = [f.name for f in model._meta.get_fields() if not f.is_relation]
    return frozenset(fields + [f"-{el}" for el in fields])


CATEGORY_ALLOWED_SORTS = _allowed_sorts(Category)
ITEMS_ALLOWED_SORTS = _allowed_sorts(Items)


def paginate(queryset: QuerySet, request: Request) -> QuerySet:
    """Apply optional ?limit=&offset= to the queryset; without limit the whole list is returned."""
    try:
        limit = int(request.GET["limit"])
    except (KeyError, ValueError):
        return queryset
    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0
    limit = min(max(limit, 0), MAX_PAGE_LIMIT)
    offset = max(offset, 0)
    end = offset + limit
    return queryset[offset:end]


class CategoryServices:
    def search_category(
        self, search_fields: CategoryFields, search_data: str, sort_type: str = "id"
    ) -> QuerySet:
        if sort_type not in CATEGORY_ALLOWED_SORTS:
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
            serializer = CategorySerializer(paginate(fields, request), many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}
        else:
            cat = Category.objects.filter(parent=None).order_by("id")
            serializer = CategorySerializer(paginate(cat, request), many=True)
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
        if sort_type not in ITEMS_ALLOWED_SORTS:
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
            serializer = ItemsSerializer(paginate(fields, request), many=True)
            return {"data": serializer.data, "status": status.HTTP_200_OK}
        else:
            items = Items.objects.all().order_by("id")
            serializer = ItemsSerializer(paginate(items, request), many=True)
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
        orders = (
            Orders.objects.filter(user_id=request.user.id)
            .prefetch_related("items__item")
            .order_by("id")
        )
        serializer = OrderSerializer(paginate(orders, request), many=True)
        return {"data": serializer.data, "status": status.HTTP_200_OK}

    def orders_post(self, request: Request) -> dict:
        already_pending = {
            "data": {"details": "You already have a pending order"},
            "status": status.HTTP_400_BAD_REQUEST,
        }
        pending_order = Orders.objects.filter(
            user_id=request.user.id, status=Orders.OrderStatus.PENDING
        )
        if pending_order.exists():
            return already_pending
        data = {"status": "Pending", "price": 0}
        serializer = OrderCreationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(user=request.user)
        except IntegrityError:
            # a concurrent request created the pending order first (orders_one_pending_per_user)
            return already_pending
        return {"data": serializer.validated_data, "status": status.HTTP_201_CREATED}

    def get_or_create_order(self, request: Request, with_items: bool = False) -> Orders:
        queryset = Orders.objects.all()
        if with_items:
            queryset = queryset.prefetch_related("items__item")
        order, _ = queryset.get_or_create(
            user_id=request.user.id,
            status=Orders.OrderStatus.PENDING,
            defaults={"price": 0},
        )
        return order


# OrderItems


class OrderItemsServices:
    def get_or_create_order_items(self, item_id: int, order_id: int) -> OrderItems:
        order_items, _ = OrderItems.objects.select_for_update().get_or_create(
            item_id=item_id, order_id=order_id, defaults={"amount": 0}
        )
        return order_items
