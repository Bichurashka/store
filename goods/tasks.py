from collections import defaultdict
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from .models import Discounts, Items


def collect_items_discounts() -> dict:
    now = timezone.now()

    discounts = Discounts.objects.filter(
        start_datetime__lte=now,
        end_datetime__gte=now,
    ).select_related("category")

    discounts_by_category = defaultdict(list)
    for discount in discounts:
        discounts_by_category[discount.category.id].append(
            {
                "type": discount.type,
                "amount": discount.amount,
            }
        )

    items = Items.objects.select_related("category")

    result = {}

    for item in items:
        category = item.category
        item_discounts = []

        while category:
            item_discounts.extend(discounts_by_category.get(category.id, []))
            category = category.parent

        result[item.pk] = item_discounts

    return result


@shared_task
def recalculate_items_price() -> None:
    items_discounts = collect_items_discounts()
    items = Items.objects.in_bulk(items_discounts.keys())
    to_update = []
    for item_id, discounts in items_discounts.items():
        item = items[item_id]

        fixed_sum = Decimal("0")
        percentage_max = Decimal("0")

        for discount in discounts:
            if discount["type"] == "fixed":
                fixed_sum += discount["amount"]
            else:  # if discount["type"] == "percentage":
                percentage_max = max(percentage_max, discount["amount"])
        result_price = item.base_price
        result_price -= min(fixed_sum, item.base_price / 2)
        result_price *= (100 - percentage_max) / 100
        item.price = result_price
        to_update.append(item)

    Items.objects.bulk_update(to_update, ["price"])
