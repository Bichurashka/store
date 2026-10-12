# Deterministic test data for load testing. Uses only fields that exist in both the baseline
# (c3e1a7b) and the current schema, so both builds get identical data.
# Run: docker compose exec -T django python manage.py shell < loadtest/seed.py
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from goods.models import Category, Discounts, Items, OrderItems, Orders
from users.models import CustomUser

ROOTS, CHILDREN, GRANDCHILDREN = 5, 4, 4
ITEMS = 5000
USERS = 300
ORDERS_PER_USER = (3, 5)
ITEMS_PER_ORDER = (5, 10)
DISCOUNTS = 20
PASSWORD = "loadtest123"

rnd = random.Random(42)

if Items.objects.exists():
    print("seed: data already present, skipping")
else:
    # Categories: 3-level tree
    roots = Category.objects.bulk_create(Category(name=f"c{r}") for r in range(ROOTS))
    children = Category.objects.bulk_create(
        Category(name=f"c{r}_{c}", parent=root)
        for r, root in enumerate(roots)
        for c in range(CHILDREN)
    )
    grandchildren = Category.objects.bulk_create(
        Category(name=f"{child.name}_{g}", parent=child)
        for child in children
        for g in range(GRANDCHILDREN)
    )
    categories = roots + children + grandchildren

    # Items
    items = []
    for i in range(ITEMS):
        price = Decimal(rnd.randint(100, 100000)) / 100
        items.append(
            Items(
                category=rnd.choice(categories),
                name=f"item {i}",
                price=price,
                base_price=price,
                description=f"description of item {i}",
                sku=f"SKU{i:08d}",
            )
        )
    items = Items.objects.bulk_create(items, batch_size=1000)

    # Users: hash the password once and reuse it
    password = make_password(PASSWORD)
    users = [
        CustomUser(
            username=f"lt_user{i}",
            name=f"Load Test {i}",
            email=f"lt_user{i}@example.com",
            phone=f"7{i:010d}",
            password=password,
        )
        for i in range(USERS)
    ]
    users.append(
        CustomUser(
            username="lt_admin",
            name="Load Test Admin",
            email="lt_admin@example.com",
            phone="79999999999",
            password=password,
            is_staff=True,
            is_superuser=True,
        )
    )
    users = CustomUser.objects.bulk_create(users)

    # Closed orders history (no Pending orders: carts are created by the load test)
    orders = []
    for user in users[:USERS]:
        for _ in range(rnd.randint(*ORDERS_PER_USER)):
            status = rnd.choice([Orders.OrderStatus.PAID, Orders.OrderStatus.SHIPPED])
            orders.append(Orders(user=user, status=status, price=0))
    orders = Orders.objects.bulk_create(orders, batch_size=1000)

    order_items = []
    for order in orders:
        total = Decimal(0)
        for item in rnd.sample(items, rnd.randint(*ITEMS_PER_ORDER)):
            amount = rnd.randint(1, 5)
            total += item.price * amount
            order_items.append(OrderItems(order=order, item=item, amount=amount))
        order.price = total
    OrderItems.objects.bulk_create(order_items, batch_size=2000)
    Orders.objects.bulk_update(orders, ["price"], batch_size=1000)

    # Discounts (fixed point in time so that both builds get the same rows)
    now = timezone.now()
    Discounts.objects.bulk_create(
        Discounts(
            category=rnd.choice(categories),
            type=rnd.choice([Discounts.DiscountType.FIXED, Discounts.DiscountType.PERCENTAGE]),
            start_datetime=now + timedelta(days=30),
            end_datetime=now + timedelta(days=31),
            amount=Decimal(rnd.randint(1, 30)),
        )
        for _ in range(DISCOUNTS)
    )

print(
    "SEED:",
    f"categories={Category.objects.count()}",
    f"category_ids={min(Category.objects.values_list('id', flat=True))}"
    f"..{max(Category.objects.values_list('id', flat=True))}",
    f"items={Items.objects.count()}",
    f"item_ids={min(Items.objects.values_list('id', flat=True))}"
    f"..{max(Items.objects.values_list('id', flat=True))}",
    f"users={CustomUser.objects.count()}",
    f"orders={Orders.objects.count()}",
    f"order_items={OrderItems.objects.count()}",
    f"discounts={Discounts.objects.count()}",
)
