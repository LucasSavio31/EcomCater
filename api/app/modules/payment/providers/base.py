"""Interface abstrata de gateways de pagamento.

Adicionar um gateway novo = implementar `PaymentGateway` e registrar em
`payment/module.py`. Nada mais no sistema muda.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Method = Literal["credit_card", "pix", "boleto"]

# status normalizado do pagamento -> reflete no pedido
#   paid      -> pedido PAGO
#   pending   -> pedido AGUARDANDO PAGAMENTO
#   failed / canceled / refunded / chargeback -> pedido CANCELADO
NormalizedStatus = Literal["pending", "paid", "failed", "canceled", "refunded", "chargeback"]


@dataclass(slots=True)
class CardInput:
    number: str
    holder_name: str
    exp_month: int
    exp_year: int
    cvv: str
    installments: int = 1


@dataclass(slots=True)
class Charge:
    provider: str
    provider_charge_id: str
    method: Method
    status: NormalizedStatus
    amount_cents: int
    installments: int | None = None
    pix_qr_code: str | None = None
    pix_expires_at: str | None = None
    boleto_url: str | None = None
    boleto_barcode: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WebhookResult:
    provider_event_id: str
    provider_charge_id: str | None
    order_number: str | None
    status: NormalizedStatus | None
    raw_event: str
    signature_valid: bool = True
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RefundResult:
    ok: bool
    provider_refund_id: str | None = None
    message: str | None = None


class PaymentGateway(ABC):
    slug: str = "base"

    @abstractmethod
    async def create_charge(
        self,
        *,
        order: Any,
        method: Method,
        card: CardInput | None = None,
        installments: int = 1,
    ) -> Charge:
        ...

    @abstractmethod
    def parse_webhook(self, headers: dict[str, str], body: dict) -> WebhookResult | None:
        ...

    async def refund(self, *, payment: Any, amount_cents: int | None = None) -> RefundResult:
        return RefundResult(ok=False, message="Reembolso não suportado por este gateway.")

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        return True
