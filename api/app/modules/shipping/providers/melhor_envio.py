"""Provedor Melhor Envio — cotação (/api/v2/me/shipment/calculate) + webhook de rastreio.

Docs: https://docs.melhorenvio.com.br/docs/introducao-a-api
Autenticação: Bearer token (token da conta Melhor Envio).
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.core.errors import DomainError
from app.modules.shipping.providers.base import (
    Package,
    ShippingProvider,
    ShippingRate,
    TrackingUpdate,
)

logger = logging.getLogger("shipping.melhor_envio")

# eventos de rastreio -> status normalizado do pedido
_STATUS_MAP = {
    "posted": "POSTADO",
    "released": "POSTADO",
    "generated": "POSTADO",
    "collected": "EM_TRANSITO",
    "in_transit": "EM_TRANSITO",
    "out_for_delivery": "EM_TRANSITO",
    "delivered": "ENTREGUE",
}


def _mm_to_cm(mm: int) -> float:
    return round(max(mm, 1) / 10, 2)


def _g_to_kg(g: int) -> float:
    return round(max(g, 1) / 1000, 3)


class MelhorEnvioProvider(ShippingProvider):
    slug = "melhor_envio"

    def __init__(self, *, token: str | None = None, base_url: str | None = None) -> None:
        self.token = token or settings.melhor_envio_token
        self.base_url = (base_url or settings.melhor_envio_api_url).rstrip("/")
        self.user_agent = settings.melhor_envio_user_agent

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }

    async def quote(
        self, *, origin_zip: str, dest_zip: str, packages: list[Package]
    ) -> list[ShippingRate]:
        if not self.token:
            raise DomainError(
                "Frete não configurado: informe o token do Melhor Envio no admin.",
                code="shipping_not_configured",
            )
        # consolida em um único volume (soma de pesos, maior dimensão)
        total_w = sum(p.weight_grams * p.quantity for p in packages) or 1
        length = max((p.length_mm for p in packages), default=160)
        width = max((p.width_mm for p in packages), default=110)
        height = sum(p.height_mm * p.quantity for p in packages) or 20
        insurance = sum(p.insurance_cents * p.quantity for p in packages) / 100

        payload = {
            "from": {"postal_code": origin_zip},
            "to": {"postal_code": dest_zip},
            "package": {
                "weight": _g_to_kg(total_w),
                "width": _mm_to_cm(width),
                "height": _mm_to_cm(height),
                "length": _mm_to_cm(length),
            },
            "options": {"insurance_value": round(insurance, 2), "receipt": False, "own_hand": False},
        }

        url = f"{self.base_url}/api/v2/me/shipment/calculate"
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                resp = await c.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Melhor Envio indisponível: %s", exc)
            raise DomainError(
                "Não foi possível calcular o frete agora. Tente novamente em instantes.",
                code="shipping_unavailable",
            ) from exc

        rates: list[ShippingRate] = []
        for svc in data if isinstance(data, list) else []:
            if svc.get("error"):
                continue
            price = svc.get("custom_price") or svc.get("price") or "0"
            try:
                price_cents = int(round(float(price) * 100))
            except (TypeError, ValueError):
                continue
            company = svc.get("company") or {}
            rates.append(
                ShippingRate(
                    id=str(svc.get("id")),
                    service=svc.get("name", "Serviço"),
                    carrier=company.get("name", "Transportadora"),
                    price_cents=price_cents,
                    delivery_days=int(svc.get("delivery_time") or svc.get("delivery_range", {}).get("max") or 0),
                    provider=self.slug,
                    extra={"company_id": company.get("id"), "picture": company.get("picture")},
                )
            )
        rates.sort(key=lambda r: r.price_cents)
        return rates

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        # Melhor Envio não assina o webhook por HMAC; validação por token na querystring
        # ou allowlist de IP é feita no router. Aqui apenas aceita.
        return True

    def parse_webhook(self, headers: dict[str, str], body: dict) -> TrackingUpdate | None:
        event = (body.get("event") or body.get("type") or "").lower()
        data = body.get("data") or body
        raw_status = (
            data.get("status")
            or data.get("tracking", {}).get("status")
            or event.split(".")[-1]
        )
        key = str(raw_status).lower()
        normalized = _STATUS_MAP.get(key)
        if not normalized:
            for k, v in _STATUS_MAP.items():
                if k in key:
                    normalized = v
                    break
        if not normalized:
            return None
        return TrackingUpdate(
            provider_shipment_id=str(data.get("id") or data.get("order_id") or ""),
            status=normalized,
            raw_status=str(raw_status),
            tracking_code=data.get("tracking") if isinstance(data.get("tracking"), str) else data.get("tracking_code"),
            occurred_at=data.get("occurred_at") or data.get("date"),
        )
