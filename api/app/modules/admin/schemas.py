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
    totp_enabled: bool = False

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


class RevenuePoint(BaseModel):
    label: str
    cents: int


class AbcPoint(BaseModel):
    name: str
    revenue_cents: int
    cum_pct: float
    cls: str  # "A" | "B" | "C"


class TopProduct(BaseModel):
    name: str
    sku: str
    units: int
    revenue_cents: int


class DashboardOut(BaseModel):
    window_days: int              # tamanho do período considerado (padrão 30)
    orders_period: int            # pedidos criados no período
    orders_pending: int          # aguardando pagamento (foto atual)
    orders_late: int             # atrasados (foto atual)
    orders_to_ship: int          # pendentes de envio (foto atual)
    orders_canceled: int         # cancelados no período
    orders_refunded: int         # estornados no período
    revenue_period_cents: int    # faturamento (pago) no período
    total_orders_all_time: int   # histórico — nunca zera
    series_metric: str           # "revenue" | "canceled" | "refunded"
    series_current: list[RevenuePoint]
    series_previous: list[RevenuePoint]
    abc_curve: list[AbcPoint]
    top_products: list[TopProduct]
