"""Load scenario shared by the baseline and the current build.

Profile is selected with LT_PROFILE: smoke | warmup | load | stress | spike.
Every virtual user logs in as its own seeded account (lt_user0..N), so carts do not
contend for the same rows.
"""

import itertools
import os
import random
import threading

from locust import HttpUser, LoadTestShape, between, task

PASSWORD = "loadtest123"
SEEDED_USERS = int(os.environ.get("LT_USERS", 300))
ITEM_IDS = (1, int(os.environ.get("LT_ITEM_MAX", 5000)))
CATEGORY_IDS = (1, int(os.environ.get("LT_CATEGORY_MAX", 105)))
PROFILE = os.environ.get("LT_PROFILE", "load")

_counter = itertools.count()
_lock = threading.Lock()


def next_username() -> str:
    with _lock:
        return f"lt_user{next(_counter) % SEEDED_USERS}"


class ShopUser(HttpUser):
    wait_time = between(1, 2)
    network_timeout = 60
    connection_timeout = 10

    def on_start(self) -> None:
        resp = self.client.post(
            "/api/v1/token/",
            json={"username": next_username(), "password": PASSWORD},
            name="POST /api/v1/token/ (login)",
        )
        # resp.ok raises on connection errors and would kill the virtual user; a user whose
        # login failed keeps running without a token (its requests then fail with 401)
        token = resp.json()["access"] if resp.status_code == 200 else ""
        self.client.headers["Authorization"] = f"Bearer {token}"

    @task(2)
    def index(self) -> None:
        self.client.get("/index", name="GET /index")

    @task(1)
    def index_category(self) -> None:
        self.client.get(
            f"/index?category={random.randint(*CATEGORY_IDS)}", name="GET /index?category=[id]"
        )

    @task(3)
    def categories(self) -> None:
        self.client.get("/api/v1/goods/category/", name="GET /api/v1/goods/category/")

    @task(3)
    def items(self) -> None:
        self.client.get("/api/v1/goods/items/", name="GET /api/v1/goods/items/")

    @task(2)
    def one_item(self) -> None:
        self.client.get(
            f"/api/v1/goods/items/{random.randint(*ITEM_IDS)}/",
            name="GET /api/v1/goods/items/[id]/",
        )

    @task(2)
    def orders(self) -> None:
        self.client.get("/api/v1/goods/orders/", name="GET /api/v1/goods/orders/")

    @task(2)
    def cart(self) -> None:
        self.client.get("/api/v1/goods/order/", name="GET /api/v1/goods/order/")

    @task(2)
    def add_to_cart(self) -> None:
        self.client.post(
            "/api/v1/goods/order_items/",
            json={"item": random.randint(*ITEM_IDS), "amount": 1},
            name="POST /api/v1/goods/order_items/",
        )

    @task(1)
    def me(self) -> None:
        self.client.get("/api/v1/users/me/", name="GET /api/v1/users/me/")


# (end of stage in seconds, users, spawn rate)
PROFILES: dict[str, list[tuple[int, int, float]]] = {
    "smoke": [(20, 1, 1)],
    "warmup": [(30, 5, 5)],
    "load": [(180, 20, 5)],
    "stress": [(120, 10, 10), (240, 25, 10), (360, 50, 10), (480, 100, 20), (600, 200, 20)],
    "spike": [(30, 5, 5), (100, 150, 15), (130, 5, 50)],
}


class ProfileShape(LoadTestShape):
    stages = PROFILES[PROFILE]

    def tick(self) -> tuple[int, float] | None:
        run_time = self.get_run_time()
        for end, users, rate in self.stages:
            if run_time < end:
                return users, rate
        return None
