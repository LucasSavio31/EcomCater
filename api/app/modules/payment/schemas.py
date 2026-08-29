"""DTOs do módulo `payment`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CardIn(BaseModel):
    number: str = Field(min_length=12, max_length=19)
    holder_name: str
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2024, le=2100)
    cvv: str = Field(min_length=3, max_length=4)
    installments: int = Field(default=1, ge=1, le=12)


class ChargeIn(BaseModel):
    order_number: str
    method: str  # credit_card | pix | boleto
    card: CardIn | None = None


class ChargeOut(BaseModel):
    payment_id: str
    order_number: str
    method: str
    status: str
    amount_cents: int
    pix_qr_code: str | None = None
    pix_expires_at: str | None = None
    boleto_url: str | None = None
    boleto_barcode: str | None = None


class PaymentStatusOut(BaseModel):
    order_number: str
    order_status: str
    payment_status: str
    method: str | None
    updated_at: str | None


class PaymentConfigOut(BaseModel):
    active_provider: str
    appmax_sandbox: bool
    has_token: bool
    methods: dict
    max_installments: int


class PaymentConfigIn(BaseModel):
    active_provider: str | None = None
    appmax_access_token: str | None = None
    appmax_sandbox: bool | None = None
    appmax_webhook_secret: str | None = None
    methods: dict | None = None
    max_installments: int | None = None


class RefundIn(BaseModel):
    amount_cents: int | None = None
