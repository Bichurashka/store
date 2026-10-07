from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ResponseWrapper(BaseModel):
    project: str = "Bichurashka`s store"
    api_version: str = "v1"
    data: Any = None


_RESPONSE_DEFAULTS = ResponseWrapper().model_dump(exclude={"data"})


def wrap_response(data: Any) -> dict[str, Any]:
    """Same shape as ResponseWrapper(data=...).model_dump(), without pydantic walking the payload"""
    return {**_RESPONSE_DEFAULTS, "data": data}


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
