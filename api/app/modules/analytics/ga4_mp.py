"""GA4 Measurement Protocol (server-side).

Usado só para eventos que acontecem SEM o navegador do cliente aberto — hoje
apenas `refund` (quando o admin estorna um pedido). Os demais eventos de
e-commerce saem pelo `dataLayer` no navegador.

Doc: https://developers.google.com/analytics/devguides/collection/protocol/ga4
"""
from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger("analytics.ga4_mp")

_ENDPOINT = "https://www.google-analytics.com/mp/collect"


async def send_event(
    *,
    measurement_id: str,
    api_secret: str,
    client_id: str,
    name: str,
    params: dict,
) -> bool:
    """Dispara um evento para o GA4. Nunca levanta — loga e devolve bool."""
    payload = {
        "client_id": client_id,
        "timestamp_micros": int(time.time() * 1_000_000),
        "non_personalized_ads": False,
        "events": [{"name": name, "params": params}],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _ENDPOINT,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning("GA4 MP %s falhou (%s): %s", name, resp.status_code, resp.text[:300])
            return False
        logger.info("GA4 MP %s enviado (client_id=%s)", name, client_id)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("GA4 MP %s: erro de rede", name)
        return False


def refund_params(order, items: list) -> dict:
    """Monta os params do `refund` no formato GA4 e-commerce (reembolso total)."""
    ga_items = [
        {
            "item_id": it.sku,
            "item_name": it.name,
            "item_variant": it.variant_label or None,
            "price": round(it.unit_price_cents / 100, 2),
            "quantity": it.quantity,
        }
        for it in items
    ]
    # value do refund = soma dos itens (regra GA4: sem frete/tax)
    value = round(sum(it.unit_price_cents * it.quantity for it in items) / 100, 2)
    return {
        "currency": order.currency or "BRL",
        "value": value,
        "transaction_id": order.number,
        "shipping": round((order.shipping_cents or 0) / 100, 2),
        "tax": 0,
        "items": [{k: v for k, v in it.items() if v is not None} for it in ga_items],
    }
