"""Gateway Appmax (API v3).

Docs: https://docs.appmax.com.br/api-reference/introduction
Conferido contra o plugin oficial WooCommerce da Appmax (`includes/class-awc-api.php`
e afins) — é a única fonte confiável do formato real da API que temos.
Autenticação: `access-token` da conta Appmax enviado no HEADER (não no corpo).
`settings.appmax_api_url` já termina em `/api/v3` — os paths aqui são relativos
a isso (`/customer`, não `/api/v3/customer`; dobrar o prefixo 404a tudo).
Fluxo: cria cliente -> cria pedido (order) -> cria pagamento (pix | credit-card | boleto).
Confirmação real vem por webhook.

Status real da Appmax (`data.status` do webhook, plugin oficial `AWC_Status_Appmax`):
  autorizado, aprovado -> paid | integrado -> pending
Nome de evento é só um heurístico de reserva pros casos que a Appmax não
manda `data.status` (refund/chargeback/cancelamento não estão no enum acima).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

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

# nome de evento (após normalizar: minúsculo, sem "_"/".") -> heurística de
# reserva, só usada quando o webhook não vem com `data.status` (a lista
# oficial de 21 eventos da Appmax usa snake_case, ex. "order_paid",
# "order_authorized", "order_pix_created" -- confirmado na doc appmax.readme.io).
_EVENT_MAP: dict[str, str] = {
    "orderapproved": "paid",
    "orderauthorized": "paid",
    "orderpaid": "paid",
    "orderpaidbypix": "paid",
    "orderpaidbycreditcard": "paid",
    "paymentapproved": "paid",
    "orderintegrated": "pending",
    "orderpendingintegration": "pending",
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

# `data.status` real da Appmax (plugin oficial `AWC_Status_Appmax`) -- quando
# presente, tem prioridade sobre o nome do evento.
_STATUS_MAP: dict[str, str] = {
    "autorizado": "paid",
    "aprovado": "paid",
    "integrado": "pending",
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
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json", "access-token": self.access_token}
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                resp = await c.post(url, json=payload, headers=headers)
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
        marketing = order.marketing_json or {}
        data = await self._post(
            "/customer",
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
                "ip": marketing.get("client_ip", ""),
                "tracking": {
                    "utm_source": marketing.get("utm_source", ""),
                    "utm_medium": marketing.get("utm_medium", ""),
                    "utm_campaign": marketing.get("utm_campaign", ""),
                    "utm_term": marketing.get("utm_term", ""),
                    "utm_content": marketing.get("utm_content", ""),
                },
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
                "description": it.name,
            }
            for it in order.items
        ]
        marketing = order.marketing_json or {}
        data = await self._post(
            "/order",
            {
                "customer_id": customer_id,
                "products": products,
                "shipping": round(order.shipping_cents / 100, 2),
                "discount": round(order.discount_cents / 100, 2),
                "freight_type": order.shipping_method or "",
                "ip": marketing.get("client_ip", ""),
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
                "/payment/pix",
                {
                    "cart": {"order_id": appmax_order_id},
                    "customer": {"customer_id": customer_id},
                    "payment": {"pix": {"document_number": order.cpf or ""}},
                },
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
            due_date = (datetime.now(UTC) + timedelta(days=3)).strftime("%Y-%m-%d")
            data = await self._post(
                "/payment/boleto",
                {
                    "cart": {"order_id": appmax_order_id},
                    "customer": {"customer_id": customer_id},
                    "payment": {"Boleto": {"document_number": order.cpf or "", "due_date": due_date}},
                },
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
            "/payment/credit-card",
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
        # o plugin oficial nunca lê status na resposta síncrona de criação do
        # pagamento -- só confirma via webhook (`data.status` == autorizado/
        # aprovado). Reportar "paid" aqui sem essa confirmação arriscava marcar
        # pedido como pago com base num campo que a resposta pode nem ter.
        return Charge(
            provider=self.slug,
            provider_charge_id=str(data.get("id") or appmax_order_id),
            method="credit_card",
            status="pending",
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
        # `data.status` (vocabulário real confirmado: autorizado/aprovado/
        # integrado) tem prioridade -- o nome do evento é só reserva pros
        # casos sem esse campo (refund/chargeback/cancelamento).
        status = _STATUS_MAP.get(str(data.get("status") or "").strip().lower())
        if status is None:
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
        # ATENÇÃO: não há endpoint de reembolso no plugin oficial da Appmax --
        # lá, reembolso só chega passivamente via webhook `order_refund`, nunca
        # é disparado pela loja. Este path/formato não está confirmado contra
        # a API real; se a Appmax não oferecer refund via API, isto vai falhar
        # (ou pior, 404 silencioso) -- reembolso real pode precisar ser feito
        # manualmente no painel da Appmax até confirmar isso com o suporte deles.
        try:
            data = await self._post(
                "/refund",
                {"order_id": payment.provider_charge_id, "amount": round((amount_cents or payment.amount_cents) / 100, 2)},
            )
        except PaymentError as exc:
            return RefundResult(ok=False, message=str(exc))
        return RefundResult(ok=True, provider_refund_id=str(data.get("id", "")))
