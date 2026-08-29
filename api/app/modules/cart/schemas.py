"""DTOs do módulo `cart`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AddItemIn(BaseModel):
    variant_id: str
    quantity: int = Field(default=1, ge=1, le=99)


class UpdateItemIn(BaseModel):
    quantity: int = Field(ge=0, le=99)


class SetZipIn(BaseModel):
    zip: str = Field(min_length=8, max_length=8)


class ApplyCouponIn(BaseModel):
    code: str


class SelectShippingIn(BaseModel):
    service_id: str


class CartItemOut(BaseModel):
    id: str
    product_id: str
    variant_id: str
    product_name: str
    product_slug: str
    variant_label: str | None
    sku: str
    image_url: str | None
    unit_price_cents: int
    quantity: int
    line_total_cents: int
    in_stock: bool
    max_qty: int
    price_changed: bool


class CartTotalsOut(BaseModel):
    items_count: int
    items_total_cents: int
    discount_cents: int
    shipping_cents: int
    grand_total_cents: int
    free_shipping_threshold_cents: int | None
    free_shipping_remaining_cents: int | None


class CartOut(BaseModel):
    token: str
    items: list[CartItemOut]
    totals: CartTotalsOut
    coupon_code: str | None
    coupon_error: str | None
    shipping_zip: str | None
    selected_shipping: dict | None
