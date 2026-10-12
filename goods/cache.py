import time
from typing import Any, Callable, cast

from django.core.cache import cache

# Safety net: entries also expire on their own if an invalidation is ever missed
CACHE_TTL = 300

CATEGORIES = "categories"
ITEMS = "items"


def _version_key(namespace: str) -> str:
    return f"goods:{namespace}:v"


def _version(namespace: str) -> int:
    # Start from a timestamp, not 1: if the version key is evicted, old entries must not match again
    return cast(int, cache.get_or_set(_version_key(namespace), time.time_ns, None))


def invalidate(namespace: str) -> None:
    """Make every cached entry of the namespace stale by bumping its version"""
    try:
        cache.incr(_version_key(namespace))
    except ValueError:  # no version stored yet (or it was evicted)
        cache.set(_version_key(namespace), time.time_ns(), None)


def get_or_build(namespace: str, suffix: str, builder: Callable[[], Any]) -> Any:
    key = f"goods:{namespace}:{_version(namespace)}:{suffix}"
    return cache.get_or_set(key, builder, CACHE_TTL)
