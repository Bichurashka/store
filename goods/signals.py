from typing import Any, Type

from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import OrderItems, Orders


def recalculate_price(order_id: int) -> None:
    # Single UPDATE ... SET price = (SELECT SUM(...)) instead of SELECT order + aggregate + UPDATE
    total = (
        OrderItems.objects.filter(order_id=OuterRef("pk"))
        .values("order_id")
        .annotate(
            total=Sum(
                ExpressionWrapper(F("item__price") * F("amount"), output_field=DecimalField())
            )
        )
        .values("total")
    )
    Orders.objects.filter(pk=order_id).update(
        price=Coalesce(Subquery(total), Value(0), output_field=DecimalField())
    )


@receiver(post_save, sender=OrderItems)
@receiver(post_delete, sender=OrderItems)
def update_order_price(sender: Type[OrderItems], instance: OrderItems, **kwargs: Any) -> None:
    recalculate_price(instance.order_id)
    # keep an already loaded order object in sync with the DB without an extra query otherwise
    if OrderItems.order.is_cached(instance):
        try:
            instance.order.refresh_from_db(fields=["price"])
        except Orders.DoesNotExist:  # the order itself is being deleted (cascade)
            pass
