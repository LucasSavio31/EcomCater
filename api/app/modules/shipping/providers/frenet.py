"""Provedor Frenet — cotação (`api.frenet.com.br`) + rastreio + emissão de
etiqueta (`whitelabel.frenet.com.br`).

Docs: https://docs.frenet.com.br/reference/getshippinginfo
Conferido contra o código-fonte real do plugin oficial WooCommerce da Frenet
(github.com/FrenetGatewaydeFretes/woo-shipping-gateway) -- cotação usa só o
header `token` (confirmado: é tudo que o plugin usa). Emissão de etiqueta
usa uma API separada (`whitelabel.frenet.com.br/v1`) que exige TAMBÉM o
header `x-partner-token` -- esse token não aparece em nenhum lugar do
plugin oficial, ou seja, não é algo que toda conta Frenet tem liberado por
padrão. Cotação e rastreio funcionam com qualquer conta; emissão de
etiqueta pode exigir pedir esse acesso ao suporte comercial da Frenet.
"""
from __future__ import annotations

import logging

import httpx

from app.core.errors import DomainError
from app.modules.shipping.providers.base import (
    Package,
    ShippingProvider,
    ShippingRate,
    TrackingUpdate,
)

logger = logging.getLogger("shipping.frenet")

_QUOTE_URL = "https://api.frenet.com.br/shipping/quote"
_TRACKING_URL = "https://api.frenet.com.br/tracking/trackinginfo"
_WHITELABEL_BASE = "https://whitelabel.frenet.com.br/v1"

# EventType do webhook/rastreio da Frenet -> status normalizado do pedido
# (confirmado em docs.frenet.com.br/docs/webhook-atualização-de-tracking).
_EVENT_TYPE_MAP: dict[int, str] = {
    18: "POSTADO",   # aguardando coleta no ponto de postagem
    0: "POSTADO",    # postado
    1: "EM_TRANSITO",
    2: "EM_TRANSITO",  # atraso -- ainda em trânsito, só atrasado
    5: "EM_TRANSITO",  # em rota / last-mile
    9: "ENTREGUE",
    # 3 (devolvido) e 4 (extravio) não têm status normalizado equivalente
    # aqui -- fica sem mapa (`parse_webhook` ignora o evento).
}


def _mm_to_cm(mm: int) -> float:
    return round(max(mm, 1) / 10, 2)


def _g_to_kg(g: int) -> float:
    return round(max(g, 1) / 1000, 3)


class FrenetProvider(ShippingProvider):
    slug = "frenet"

    def __init__(
        self, *, token: str = "", partner_token: str = "",
        webhook_header_name: str = "", webhook_header_value: str = "",
    ) -> None:
        self.token = token
        self.partner_token = partner_token
        self.webhook_header_name = webhook_header_name
        self.webhook_header_value = webhook_header_value

    def _headers(self) -> dict[str, str]:
        return {"token": self.token, "Content-Type": "application/json", "Accept": "application/json"}

    def _partner_headers(self) -> dict[str, str]:
        if not self.partner_token:
            raise DomainError(
                "Emissão de etiqueta pela Frenet exige um Token de parceiro "
                "(whitelabel) -- solicite ao suporte comercial da Frenet e "
                "configure em Frete → Provedores de frete.",
                code="shipping_partner_token_missing",
            )
        return {**self._headers(), "x-partner-token": self.partner_token}

    async def quote(
        self, *, origin_zip: str, dest_zip: str, packages: list[Package]
    ) -> list[ShippingRate]:
        if not self.token:
            raise DomainError(
                "Frete não configurado: informe o token da Frenet no admin.",
                code="shipping_not_configured",
            )
        items = [
            {
                "Weight": _g_to_kg(p.weight_grams),
                "Length": _mm_to_cm(p.length_mm),
                "Height": _mm_to_cm(p.height_mm),
                "Width": _mm_to_cm(p.width_mm),
                "Quantity": p.quantity,
            }
            for p in packages
        ]
        invoice_value = round(sum(p.insurance_cents * p.quantity for p in packages) / 100, 2)
        payload = {
            "SellerCEP": origin_zip,
            "RecipientCEP": dest_zip,
            "ShipmentInvoiceValue": invoice_value or 1,
            "RecipientCountry": "BR",
            "ShippingItemArray": items,
        }
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                resp = await c.post(_QUOTE_URL, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Frenet indisponível: %s", exc)
            raise DomainError(
                "Não foi possível calcular o frete agora. Tente novamente em instantes.",
                code="shipping_unavailable",
            ) from exc

        rates: list[ShippingRate] = []
        for svc in (data or {}).get("ShippingSevicesArray") or []:
            if svc.get("Error"):
                continue
            try:
                price_cents = int(round(float(svc.get("ShippingPrice") or 0) * 100))
            except (TypeError, ValueError):
                continue
            try:
                delivery_days = int(float(svc.get("DeliveryTime") or 0))
            except (TypeError, ValueError):
                delivery_days = 0
            rates.append(
                ShippingRate(
                    id=str(svc.get("ServiceCode")),
                    service=svc.get("ServiceDescription", "Serviço"),
                    carrier=svc.get("Carrier", "Transportadora"),
                    price_cents=price_cents,
                    delivery_days=delivery_days,
                    provider=self.slug,
                    extra={"carrier_code": svc.get("CarrierCode")},
                )
            )
        rates.sort(key=lambda r: r.price_cents)
        return rates

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        # A Frenet não assina o webhook -- o único mecanismo de verificação é
        # um header customizado que o próprio lojista escolhe (nome/valor) ao
        # cadastrar a URL no painel da Frenet. Sem isso configurado: RECUSA
        # (falha fechada) -- mesmo raciocínio já usado pro webhook do ME
        # (token na querystring), só que aqui o nome do header também é livre.
        if not self.webhook_header_name or not self.webhook_header_value:
            logger.warning(
                "webhook Frenet recusado: nenhum header de verificação configurado "
                "(menu Frete → Provedores de frete)"
            )
            return False
        return headers.get(self.webhook_header_name.lower()) == self.webhook_header_value

    def parse_webhook(self, headers: dict[str, str], body: dict) -> TrackingUpdate | None:
        events = body.get("TrackingEvents") or []
        normalized: str | None = None
        raw_status = ""
        for evt in events:
            try:
                event_type = int(evt.get("EventType"))
            except (TypeError, ValueError):
                continue
            mapped = _EVENT_TYPE_MAP.get(event_type)
            if mapped:
                # o último evento relevante da lista é o mais recente
                normalized = mapped
                raw_status = str(event_type)
        if not normalized:
            return None
        return TrackingUpdate(
            provider_shipment_id=str(body.get("ShipmentId") or ""),
            status=normalized,
            raw_status=raw_status,
            tracking_code=body.get("TrackingNumber"),
            occurred_at=None,
        )

    # -------------------------------------------------- emissão de etiqueta
    # (fora da interface `ShippingProvider` -- só usados pelas funções
    # `_frenet_*`/`frenet_*` de `shipping/service.py`, mesmo espírito de como
    # `_me_label_for_order` chama a API do Melhor Envio direto via httpx.)

    async def create_shipment(self, shipment: dict) -> dict:
        """POST /shipments -- cria o(s) envio(s) na Frenet. `shipment` é um
        único objeto Shipment (Order/Quotation/Volumes); a API aceita um
        array, mandamos sempre com 1 item."""
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(
                f"{_WHITELABEL_BASE}/shipments", json=[shipment], headers=self._partner_headers()
            )
        data = _safe_json(resp)
        if resp.status_code >= 400:
            raise DomainError(_frenet_err("criar envio", resp, data), code="shipping_error")
        return data

    async def checkout(self, shipment_ids: list[int]) -> dict:
        """POST /shipments/checkout -- compra os envios (debita saldo/gera
        cobrança). `Status: 1` = pago na hora, `2` = aguardando pagamento."""
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(
                f"{_WHITELABEL_BASE}/shipments/checkout",
                json=shipment_ids,
                headers=self._partner_headers(),
            )
        data = _safe_json(resp)
        if resp.status_code >= 400:
            raise DomainError(_frenet_err("checkout", resp, data), code="shipping_error")
        return data

    async def get_label(self, shipment_id: int | str) -> dict:
        """GET /shipments/{id}/label -- devolve `LabelUrl`/`TrackingUrl` etc.
        (não o PDF em si; é preciso baixar a `LabelUrl` à parte)."""
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(
                f"{_WHITELABEL_BASE}/shipments/{shipment_id}/label", headers=self._partner_headers()
            )
        data = _safe_json(resp)
        if resp.status_code >= 400:
            raise DomainError(_frenet_err("obter etiqueta", resp, data), code="shipping_error")
        return data

    async def track(self, *, service_code: str, tracking_number: str) -> dict:
        """POST /tracking/trackinginfo -- status real de UM envio (a Frenet
        não tem endpoint de consulta em lote como o Melhor Envio)."""
        payload = {"ShippingServiceCode": service_code, "TrackingNumber": tracking_number}
        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.post(_TRACKING_URL, json=payload, headers=self._headers())
        return _safe_json(resp)


def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {}


def _frenet_err(step: str, resp: httpx.Response, data: dict) -> str:
    msg = None
    if isinstance(data, dict):
        errors = data.get("Errors")
        if isinstance(errors, list) and errors:
            msg = "; ".join(str(e) for e in errors)
        msg = msg or data.get("Message") or data.get("message")
    return f"Frenet recusou {step} (HTTP {resp.status_code}): {msg or resp.text[:200]}"
