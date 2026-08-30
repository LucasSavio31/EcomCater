"""DTOs do módulo `shipping`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class QuoteItemIn(BaseModel):
    weight_grams: int = 300
    length_mm: int = 200
    width_mm: int = 150
    height_mm: int = 100
    price_cents: int = 0
    quantity: int = 1


class QuoteIn(BaseModel):
    dest_zip: str = Field(min_length=8, max_length=8)
    items: list[QuoteItemIn] | None = None


class RateOut(BaseModel):
    id: str
    service: str
    carrier: str
    price_cents: int
    delivery_days: int
    provider: str


class ShippingConfigOut(BaseModel):
    active_provider: str
    origin_zip: str
    melhor_envio_sandbox: bool
    has_token: bool
    default_package: dict
    free_shipping_services: list[str]
    free_shipping_all: bool = False
    free_shipping_min_cents: int | None = None


class ShippingConfigIn(BaseModel):
    active_provider: str | None = None
    origin_zip: str | None = None
    melhor_envio_token: str | None = None
    melhor_envio_sandbox: bool | None = None
    webhook_token: str | None = None
    default_package: dict | None = None
    free_shipping_services: list[str] | None = None
    free_shipping_all: bool | None = None
    free_shipping_min_cents: int | None = None
