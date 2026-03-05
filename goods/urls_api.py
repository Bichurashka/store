from django.urls import path

from goods.views_api import (
    category_view,
    items_view,
    one_category_view,
    one_item_view,
    one_order_view,
    order_item_view,
    order_items_view,
    orders_view,
)

urlpatterns = [
    path("category/", category_view, name="category"),
    path("category/<int:cat_id>/", one_category_view, name="one_category"),
    path("items/", items_view, name="items"),
    path("items/<int:item_id>/", one_item_view, name="one_item"),
    path("orders/", orders_view, name="orders"),
    path("order/", one_order_view, name="one_order"),
    path("order_items/", order_items_view, name="order_items"),
    path("order_item/<int:item_id>/", order_item_view, name="order_item"),
]
