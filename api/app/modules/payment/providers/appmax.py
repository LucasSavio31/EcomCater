"""Gateway Appmax (API v2/v3).

Docs: https://docs.appmax.com.br/api-reference/introduction
Autenticação: `access-token` da conta Appmax enviado no corpo de cada requisição.
Fluxo: cria cliente -> cria pedido (order) -> cria pagamento (pix | credit-card | boleto).
Confirmação real vem por webhook.

Eventos de webhook -> status normalizado (usuário: PAGO / AGUARDANDO PAGAMENTO / CANCELADO):
  OrderApproved, OrderPaid, OrderPaidByPix, PaymentApproved      -> paid
  OrderIntegrated, OrderPending, PixGenerated, BoletoGenerated   -> pending
  OrderRefund, OrderChargeback                                   -> refunded / chargeback
  PaymentNotAuthorized, OrderBilletOverdue, PixExpired, OrderCancelled -> failed / canceled
"""
from __future__ import annotations

import logging

import httpx

from app.core.errors import PaymentError
from app.modules.payment.providers.base import (
    CardInput,
    Charge,
    Method,
    PaymentGateway,
    RefundResult,
    WebhookResult,
)

logger = logging.getLogger("payment.appmax")

_EVENT_MAP: dict[str, str] = {
    "orderapproved": "paid",
    "orderpaid": "paid",
    "orderpaidbypix": "paid",
    "orderpaidbycreditcard": "paid",
    "paymentapproved": "paid",
    "orderintegrated": "pending",
    "orderpending": "pending",
    "orderpixcreated": "pending",
    "pixgenerated": "pending",
    "orderbilletcreated": "pending",
    "billetgenerated": "pending",
    "orderrefund": "refunded",
    "orderchargeback": "chargeback",
    "paymentnotauthorized": "failed",
    "orderbilletoverdue": "canceled",
    "pixexpired": "canceled",
    "ordercancelled": "canceled",
    "ordercanceled": "canceled",
}


class AppmaxGateway(PaymentGateway):
    slug = "appmax"

    def __init__(self, *, access_token: str, base_url: str, webhook_secret: str = "") -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.webhook_secret = webhook_secret

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.access_token:
            raise PaymentError(
                "Pagamento não configurado: informe o token da Appmax no admin.",
                code="payment_not_configured",
            )
        body = {"access-token": self.access_token, **payload}
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                resp = await c.post(url, json=body, headers={"Content-Type": "application/json"})
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Appmax indisponível: %s", exc)
            raise PaymentError("Falha de comunicação com o gateway de pagamento.") from exc
        if resp.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
            msg = data.get("text") or data.get("message") or "Pagamento recusado."
            raise PaymentError(str(msg), details={"appmax": data})
        return data.get("data", data) if isinstance(data, dict) else {}

    async def _ensure_customer(self, order) -> str:
        addr = order.shipping_address_json or {}
        name = addr.get("recipient_name", order.email.split("@")[0])
        first, _, last = name.partition(" ")
        data = await self._post(
            "/api/v3/customer",
            {
                "firstname": first or name,
                "lastname": last or ".",
                "email": order.email,
                "telephone": addr.get("phone", ""),
                "postcode": addr.get("zip", ""),
                "address_street": addr.get("street", ""),
                "address_street_number": addr.get("number", ""),
                "address_street_complement": addr.get("complement", ""),
                "address_street_district": addr.get("district", ""),
                "address_city": addr.get("city", ""),
                "address_state": addr.get("state", ""),
                "document": order.cpf or "",
            },
        )
        return str(data.get("id") or data.get("customer_id"))

    async def _create_order(self, order, customer_id: str) -> str:
        products = [
            {
                "sku": it.sku,
                "name": it.name,
                "qty": it.quantity,
                "price": round(it.unit_price_cents / 100, 2),
            }
            for it in order.items
        ]
        data = await self._post(
            "/api/v3/order",
            {
                "customer_id": customer_id,
                "products": products,
                "shipping": round(order.shipping_cents / 100, 2),
                "discount": round(order.discount_cents / 100, 2),
                "total": round(order.grand_total_cents / 100, 2),
                "external_id": order.number,
            },
        )
        return str(data.get("id") or data.get("order_id"))

    async def create_charge(
        self,
        *,
        order,
        method: Method,
        card: CardInput | None = None,
        installments: int = 1,
    ) -> Charge:
        customer_id = await self._ensure_customer(order)
        appmax_order_id = await self._create_order(order, customer_id)
        amount = order.grand_total_cents

        if method == "pix":
            data = await self._post(
                "/api/v3/payment/pix",
                {"cart": {"order_id": appmax_order_id}, "customer": {"customer_id": customer_id}},
            )
            return Charge(
                provider=self.slug,
                provider_charge_id=str(data.get("id") or appmax_order_id),
                method="pix",
                status="pending",
                amount_cents=amount,
                pix_qr_code=data.get("pix_emv") or data.get("qrcode") or data.get("pix_qrcode"),
                pix_expires_at=data.get("pix_expiration_date") or data.get("expiration_date"),
                raw=data,
            )

        if method == "boleto":
            data = await self._post(
                "/api/v3/payment/boleto",
                {"cart": {"order_id": appmax_order_id}, "customer": {"customer_id": customer_id}},
            )
            return Charge(
                provider=self.slug,
                provider_charge_id=str(data.get("id") or appmax_order_id),
                method="boleto",
                status="pending",
                amount_cents=amount,
                boleto_url=data.get("pdf") or data.get("boleto_url") or data.get("url"),
                boleto_barcode=data.get("digitable_line") or data.get("barcode"),
                raw=data,
            )

        if not card:
            raise PaymentError("Dados do cartão ausentes.")
        data = await self._post(
            "/api/v3/payment/credit-card",
            {
                "cart": {"order_id": appmax_order_id},
                "customer": {"customer_id": customer_id},
                "payment": {
                    "CreditCard": {
                        "number": card.number,
                        "cvv": card.cvv,
                        "month": card.exp_month,
                        "year": card.exp_year,
                        "name": card.holder_name,
                        "document_number": order.cpf or "",
                        "installments": card.installments or installments,
                    }
                },
            },
        )
        status = "paid" if str(data.get("status", "")).lower() in ("aprovado", "approved", "paid") else "pending"
        return Charge(
            provider=self.slug,
            provider_charge_id=str(data.get("id") or appmax_order_id),
            method="credit_card",
            status=status,  # type: ignore[arg-type]
            amount_cents=amount,
            installments=card.installments or installments,
            raw=data,
        )

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        # Sem segredo configurado: RECUSA (falha fechada). Confiar em qualquer
        # webhook sem verificação permitiria marcar pedido como pago sem
        # pagamento real -- é dinheiro de verdade, não pode confiar por padrão.
        if not self.webhook_secret:
            logger.warning(
                "webhook Appmax recusado: nenhum appmax_webhook_secret configurado "
                "(menu Pagamento) -- confirmações de pagamento não vão funcionar até configurar"
            )
            return False
        return headers.get("x-appmax-token") == self.webhook_secret or (
            self.webhook_secret in raw_body.decode("utf-8", "ignore")
        )

    def parse_webhook(self, headers: dict[str, str], body: dict) -> WebhookResult | None:
        event = str(body.get("event") or body.get("type") or "").replace("_", "").replace(".", "").lower()
        data = body.get("data") or body
        status = _EVENT_MAP.get(event)
        if status is None:
            for k, v in _EVENT_MAP.items():
                if k in event:
                    status = v
                    break
        return WebhookResult(
            provider_event_id=str(body.get("id") or data.get("id") or f"{event}:{data.get('order_id','')}"),
            provider_charge_id=str(data.get("id") or data.get("order_id") or "") or None,
            order_number=data.get("external_id") or data.get("order", {}).get("external_id"),
            status=status,  # type: ignore[arg-type]
            raw_event=event,
            payload=body,
        )

    async def refund(self, *, payment, amount_cents: int | None = None) -> RefundResult:
        try:
            data = await self._post(
                "/api/v3/refund",
                {"order_id": payment.provider_charge_id, "amount": round((amount_cents or payment.amount_cents) / 100, 2)},
            )
        except PaymentError as exc:
            return RefundResult(ok=False, message=str(exc))
        return RefundResult(ok=True, provider_refund_id=str(data.get("id", "")))
