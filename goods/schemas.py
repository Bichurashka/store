from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ResponseWrapper(BaseModel):
    project: str = "Bichurashka`s store"
    api_version: str = "v1"
    data: Any = None


class CategoryFilters(StrEnum):
    ID = "id"
    NAME = "name"


class CategoryFields(BaseModel):
    category_fields: list[CategoryFilters]


class ItemsFilters(StrEnum):
    ID = "id"
    NAME = "name"
    PRICE = "price"
    SKU = "sku"


class ItemsFields(BaseModel):
    items_fields: list[ItemsFilters]


class OrderItemsSchema(BaseModel):
    item: int
    amount: int
