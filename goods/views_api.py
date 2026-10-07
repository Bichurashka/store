from typing import Callable

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from goods.models import Category, Items, OrderItems, Orders
from goods.schemas import ResponseWrapper
from goods.serializers import (
    CategoryCreationSerializer,
    CategorySerializer,
    ItemsCreationSerializer,
    ItemsSerializer,
    OrderItemsCreationSerializer,
    OrderItemsInputSerializer,
    OrderSerializer,
)
from goods.services import (
    CategoryRequestsService,
    ItemsRequestsServices,
    OrderItemsServices,
    OrdersServices,
)
from users.utils import is_admin

# Categories


@api_view(["GET", "POST", "PUT"])
@is_admin("POST", "PUT")
def category_view(request: Request) -> Response:
    service = CategoryRequestsService()

    func: dict[str, Callable[[Request], dict]] = {
        "GET": service.category_get,
        "POST": service.category_post,
        "PUT": service.category_put,
    }
    func_result = func[request.method](request)
    return Response(
        ResponseWrapper(data=func_result["data"]).model_dump(),
        status=func_result["status"],
    )


@api_view(["GET", "PATCH"])
@is_admin("PATCH")
def one_category_view(request: Request, cat_id: int) -> Response:
    try:
        cat = Category.objects.get(id=cat_id)
    except Category.DoesNotExist:
        return Response({"detail": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        serializer = CategorySerializer(cat)
        return Response(ResponseWrapper(data=serializer.data).model_dump())
    else:  # elif request.method == "PATCH":
        serializer = CategoryCreationSerializer(instance=cat, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ResponseWrapper(data=serializer.validated_data).model_dump())
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Items


@api_view(["GET", "POST", "PUT"])
@is_admin("POST", "PUT")
def items_view(request: Request) -> Response:
    service = ItemsRequestsServices()
    func: dict[str, Callable[[Request], dict]] = {
        "GET": service.items_get,
        "POST": service.items_post,
        "PUT": service.items_put,
    }
    func_result = func[request.method](request)
    return Response(
        ResponseWrapper(data=func_result["data"]).model_dump(),
        status=func_result["status"],
    )


@api_view(["GET", "PATCH"])
@is_admin("PATCH")
def one_item_view(request: Request, item_id: int) -> Response:
    try:
        item = Items.objects.get(id=item_id)
    except Items.DoesNotExist:
        return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        serializer = ItemsSerializer(item)
        return Response(ResponseWrapper(data=serializer.data).model_dump())
    else:
        serializer = ItemsCreationSerializer(instance=item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ResponseWrapper(data=serializer.validated_data).model_dump())
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Orders


@api_view(["GET", "POST"])
def orders_view(request: Request) -> Response:
    service = OrdersServices()
    func: dict[str, Callable[[Request], dict]] = {
        "GET": service.orders_get,
        "POST": service.orders_post,
    }
    func_result = func[request.method](request)
    return Response(
        ResponseWrapper(data=func_result["data"]).model_dump(),
        status=func_result["status"],
    )


@api_view(["GET"])
def one_order_view(request: Request) -> Response:
    service = OrdersServices()
    order = service.get_or_create_order(request)
    serializer = OrderSerializer(order)
    return Response(ResponseWrapper(data=serializer.data).model_dump())


# OrderItems


@api_view(["POST", "PATCH"])
def order_items_view(request: Request) -> Response:
    try:
        serializer = OrderItemsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
    except ValidationError as e:
        return Response({"detail": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    try:
        item = Items.objects.get(id=validated_data["item"])
    except Items.DoesNotExist:
        return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

    service_orders = OrdersServices()
    order = service_orders.get_or_create_order(request)

    service_order_items = OrderItemsServices()
    order_items = service_order_items.get_or_create_order_items(item.pk, order.pk)

    if request.method == "POST":
        new_amount = (
            0
            if order_items.amount + validated_data["amount"] < 0
            else order_items.amount + validated_data["amount"]
        )
    else:  # PATCH
        new_amount = 0 if validated_data["amount"] < 0 else validated_data["amount"]
    order_items_data = {"amount": new_amount}
    order_items_serializer = OrderItemsCreationSerializer(
        instance=order_items, data=order_items_data, partial=True
    )
    order_items_serializer.is_valid()
    order_items_serializer.save()
    return Response(
        ResponseWrapper(data=order_items_serializer.validated_data).model_dump(),
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
def order_item_view(request: Request, item_id: int) -> Response:
    item = get_object_or_404(Items, id=item_id)
    order = get_object_or_404(Orders, user=request.user, status="Pending")
    order_item = get_object_or_404(OrderItems, item=item, order=order)
    order_item.delete()
    return Response({"detail": "Order item deleted"}, status=status.HTTP_204_NO_CONTENT)
