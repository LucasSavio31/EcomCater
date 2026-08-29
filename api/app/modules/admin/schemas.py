"""DTOs do módulo `admin`."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    must_change_password: bool
    is_active: bool
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserCreateIn(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8, max_length=128)
    role: str = "staff"


class AdminUserUpdateIn(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ModuleOut(BaseModel):
    slug: str
    label: str
    kind: str
    toggleable: bool
    enabled: bool
    config: dict


class ModuleUpdateIn(BaseModel):
    enabled: bool | None = None
    config: dict | None = None


class DashboardOut(BaseModel):
    orders_today: int
    orders_pending: int
    revenue_month_cents: int
    low_stock_count: int
    recent_orders: list[dict]
