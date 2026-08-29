"""DTOs do módulo `promotions`."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CouponBase(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    description: str | None = None
    type: str  # percent | fixed | free_shipping
    value: float = 0
    min_order_cents: int | None = None
    max_discount_cents: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    usage_limit_per_user: int | None = None
    is_active: bool = True


class CouponCreateIn(CouponBase):
    pass


class CouponUpdateIn(BaseModel):
    description: str | None = None
    type: str | None = None
    value: float | None = None
    min_order_cents: int | None = None
    max_discount_cents: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    usage_limit_per_user: int | None = None
    is_active: bool | None = None


class CouponOut(CouponBase):
    id: str
    used_count: int

    class Config:
        from_attributes = True
