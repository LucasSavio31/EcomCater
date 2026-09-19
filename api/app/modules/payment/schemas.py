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
    pix_qr_data_uri: str | None = None
    pix_expires_at: str | None = None
    boleto_url: str | None = None
    boleto_barcode: str | None = None
    boleto_barcode_data_uri: str | None = None


class PaymentStatusOut(BaseModel):
    order_number: str
    order_status: str
    payment_status: str
    method: str | None
    updated_at: str | None


class ProviderConfigIn(BaseModel):
    """Body de `PUT /config/providers/{slug}` -- campos livres em `config`
    (cada provedor usa as chaves que precisa; texto em branco = mantém o
    valor já salvo, mesmo padrão de segredo mascarado do resto do projeto)."""

    enabled: bool | None = None
    config: dict | None = None


class MethodProvidersIn(BaseModel):
    """Body de `PUT /config/method-providers` -- vínculo método -> provedor.
    Valor vazio/None num método = método desligado (nenhum provedor
    atende)."""

    credit_card: str | None = None
    pix: str | None = None
    boleto: str | None = None
    max_installments: int | None = None


class RefundIn(BaseModel):
    amount_cents: int | None = None
