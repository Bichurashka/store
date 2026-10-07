from collections import defaultdict
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from .models import Category, Discounts, Items

BATCH_SIZE = 1000


def _category_ancestors() -> dict[int, list[int]]:
    """Map category id -> [id, parent id, grandparent id, ...] built from a single query"""
    parents: dict[int, int | None] = dict(Category.objects.values_list("id", "parent_id"))
    ancestors: dict[int, list[int]] = {}

    def resolve(cat_id: int) -> list[int]:
        chain: list[int] = []
        current: int | None = cat_id
        while current is not None and current not in ancestors:
            if current in chain:  # protect from cycles in parent links
                break
            chain.append(current)
            current = parents.get(current)
        tail = ancestors[current] if current is not None and current in ancestors else []
        # memoize every category on the chain
        for i, node in enumerate(chain):
            ancestors[node] = chain[i:] + tail
        return ancestors[cat_id]

    for cat_id in parents:
        resolve(cat_id)
    return ancestors


def _discounts_by_category() -> dict[int, list[dict]]:
    now = timezone.now()
    discounts = Discounts.objects.filter(
        start_datetime__lte=now,
        end_datetime__gte=now,
    ).values("category_id", "type", "amount")

    result = defaultdict(list)
    for discount in discounts:
        result[discount["category_id"]].append(
            {
                "type": discount["type"],
                "amount": discount["amount"],
            }
        )
    return result


def _item_discounts(
    category_id: int | None,
    ancestors: dict[int, list[int]],
    discounts_by_category: dict[int, list[dict]],
) -> list[dict]:
    item_discounts = []
    for cat_id in ancestors.get(category_id, []) if category_id is not None else []:
        item_discounts.extend(discounts_by_category.get(cat_id, []))
    return item_discounts


def calculate_price(base_price: Decimal, discounts: list[dict]) -> Decimal:
    fixed_sum = Decimal("0")
    percentage_max = Decimal("0")

    for discount in discounts:
        if discount["type"] == Discounts.DiscountType.FIXED:
            fixed_sum += discount["amount"]
        else:  # Discounts.DiscountType.PERCENTAGE
            percentage_max = max(percentage_max, discount["amount"])
    result_price = base_price
    result_price -= min(fixed_sum, base_price / 2)
    result_price *= (100 - percentage_max) / 100
    return result_price


@shared_task
def recalculate_items_price() -> None:
    # Discounts and categories are small; items are read once and streamed in batches
    discounts_by_category = _discounts_by_category()
    ancestors = _category_ancestors()

    to_update = []
    items = Items.objects.only("id", "base_price", "category_id").iterator(chunk_size=BATCH_SIZE)
    for item in items:
        discounts = _item_discounts(item.category_id, ancestors, discounts_by_category)
        item.price = calculate_price(item.base_price, discounts)
        to_update.append(item)

        if len(to_update) >= BATCH_SIZE:
            Items.objects.bulk_update(to_update, ["price"])
            to_update = []

    if to_update:
        Items.objects.bulk_update(to_update, ["price"])
