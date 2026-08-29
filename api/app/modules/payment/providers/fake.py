"""Gateway falso para dev/testes (sem credenciais).

Ativado quando `active_provider = "fake"` na config do módulo `payment`.
Cartão: aprova na hora (a menos que o número termine em 0000 -> recusa).
Pix/boleto: ficam `pending` e confirmam via webhook simulado
(`POST /api/webhooks/payment/fake` com `{order_number, status}`).
"""
from __future__ import annotations

import secrets

from app.modules.payment.providers.base import (
    CardInput,
    Charge,
    Method,
    PaymentGateway,
    RefundResult,
    WebhookResult,
)


class FakeGateway(PaymentGateway):
    slug = "fake"

    async def create_charge(
        self, *, order, method: Method, card: CardInput | None = None, installments: int = 1
    ) -> Charge:
        cid = f"fake_{secrets.token_hex(8)}"
        if method == "credit_card":
            declined = card is not None and card.number.replace(" ", "").endswith("0000")
            return Charge(
                provider=self.slug,
                provider_charge_id=cid,
                method="credit_card",
                status="failed" if declined else "paid",
                amount_cents=order.grand_total_cents,
                installments=card.installments if card else installments,
                raw={"fake": True, "declined": declined},
            )
        if method == "pix":
            return Charge(
                provider=self.slug, provider_charge_id=cid, method="pix", status="pending",
                amount_cents=order.grand_total_cents,
                pix_qr_code="00020126FAKE-PIX-EMV-" + cid, pix_expires_at=None, raw={"fake": True},
            )
        return Charge(
            provider=self.slug, provider_charge_id=cid, method="boleto", status="pending",
            amount_cents=order.grand_total_cents,
            boleto_url="https://example.test/boleto/" + cid,
            boleto_barcode="00000.00000 00000.000000 00000.000000 0 00000000000000",
            raw={"fake": True},
        )

    def parse_webhook(self, headers, body) -> WebhookResult | None:
        return WebhookResult(
            provider_event_id=str(body.get("event_id") or secrets.token_hex(8)),
            provider_charge_id=body.get("charge_id"),
            order_number=body.get("order_number"),
            status=body.get("status", "paid"),
            raw_event=body.get("status", "paid"),
            payload=body,
        )

    async def refund(self, *, payment, amount_cents=None) -> RefundResult:
        return RefundResult(ok=True, provider_refund_id="fake_refund_" + secrets.token_hex(4))
