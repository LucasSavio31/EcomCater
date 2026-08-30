"""DTOs do módulo `orders`."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AddressPayload(BaseModel):
    recipient_name: str
    zip: str = Field(min_length=8, max_length=8)
    street: str
    number: str
    complement: str | None = None
    district: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    country: str = "BR"
    # telefone é coletado no checkout e repassado ao gateway / CAPI
    phone: str | None = None


class CheckoutIn(BaseModel):
    email: EmailStr
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    shipping_address: AddressPayload
    billing_address: AddressPayload | None = None
    customer_note: str | None = None
    shipping_service_id: str | None = None
    idempotency_key: str | None = None


class OrderItemOut(BaseModel):
    sku: str
    name: str
    variant_label: str | None
    image_url: str | None
    unit_price_cents: int
    quantity: int
    total_cents: int


class OrderEventOut(BaseModel):
    type: str
    from_status: str | None
    to_status: str | None
    message: str | None
    actor_type: str
    created_at: datetime | None


class OrderOut(BaseModel):
    id: str
    number: str
    status: str
    payment_status: str
    fulfillment_status: str
    email: str
    items: list[OrderItemOut]
    items_total_cents: int
    discount_cents: int
    shipping_cents: int
    grand_total_cents: int
    coupon_code: str | None
    shipping_method: str | None
    shipping_service: dict | None
    shipping_address: dict
    customer_note: str | None
    placed_at: datetime | None
    events: list[OrderEventOut]


class OrderListItem(BaseModel):
    id: str
    number: str
    status: str
    payment_status: str
    email: str
    grand_total_cents: int
    placed_at: datetime | None


class StatusChangeIn(BaseModel):
    status: str
    message: str | None = None


class NoteIn(BaseModel):
    message: str


class GuestLookupIn(BaseModel):
    number: str
    email: EmailStr
