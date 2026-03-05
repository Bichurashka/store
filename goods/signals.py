from typing import Any, Type

from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import OrderItems, Orders


def recalculate_price(order: Orders) -> None:
    total = order.items.aggregate(
        total=Coalesce(
            Sum(ExpressionWrapper(F("item__price") * F("amount"), output_field=DecimalField())),
            Value(0, output_field=DecimalField()),
        )
    )["total"]
    order.price = total
    order.save(update_fields=["price"])


@receiver(post_save, sender=OrderItems)
@receiver(post_delete, sender=OrderItems)
def update_order_price(sender: Type[OrderItems], instance: OrderItems, **kwargs: Any) -> None:
    recalculate_price(instance.order)
