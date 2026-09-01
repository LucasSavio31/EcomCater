"""Meta Conversions API (server-side) — envio de eventos de conversão.

Doc: https://developers.facebook.com/docs/marketing-api/conversions-api

Enviamos o `Purchase` quando o pedido é pago. O `event_id` é determinístico
(`purchase.<numero-do-pedido>`) e igual ao do Pixel do navegador, então a Meta
faz a deduplicação automaticamente.
"""
from __future__ import annotations

import hashlib
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger("analytics.capi")

GRAPH_VERSION = "v21.0"


def _hash(value: str | None) -> str | None:
    if not value:
        return None
    norm = value.strip().lower()
    if not norm:
        return None
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _hash_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return hashlib.sha256(digits.encode("utf-8")).hexdigest() if digits else None


async def send_event(
    *,
    pixel_id: str,
    access_token: str,
    event_name: str,
    event_id: str,
    event_source_url: str | None,
    user_data: dict,
    custom_data: dict,
    test_event_code: str | None = None,
) -> bool:
    """Dispara um evento para a Graph API. Nunca levanta — loga e devolve bool."""
    payload: dict = {
        "data": [
            {
                "event_name": event_name,
                "event_time": int(time.time()),
                "event_id": event_id,
                "action_source": "website",
                "event_source_url": event_source_url,
                "user_data": {k: v for k, v in user_data.items() if v},
                "custom_data": custom_data,
            }
        ]
    }
    if test_event_code:
        payload["test_event_code"] = test_event_code

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{pixel_id}/events"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, params={"access_token": access_token}, json=payload)
        if resp.status_code >= 400:
            logger.warning("CAPI %s falhou (%s): %s", event_name, resp.status_code, resp.text[:500])
            return False
        logger.info("CAPI %s enviado (event_id=%s)", event_name, event_id)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("CAPI %s: erro de rede", event_name)
        return False


async def send_purchase(
    *,
    pixel_id: str,
    access_token: str,
    order,
    items: list,
    test_event_code: str | None = None,
    client_ip: str | None = None,
    client_ua: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
) -> bool:
    addr = order.shipping_address_json or {}
    name_parts = (addr.get("recipient_name") or "").split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    user_data = {
        "em": [_hash(order.email)] if order.email else None,
        "ph": [_hash_phone(addr.get("phone"))] if addr.get("phone") else None,
        "fn": [_hash(first_name)] if first_name else None,
        "ln": [_hash(last_name)] if last_name else None,
        "ct": [_hash((addr.get("city") or "").replace(" ", ""))] if addr.get("city") else None,
        "st": [_hash(addr.get("state"))] if addr.get("state") else None,
        "zp": [_hash_phone(addr.get("zip"))] if addr.get("zip") else None,
        "country": [_hash(addr.get("country") or "BR")],
        "external_id": [_hash(order.cpf)] if order.cpf else None,
        "client_ip_address": client_ip,
        "client_user_agent": client_ua,
        "fbp": fbp,
        "fbc": fbc,
    }
    contents = [
        {"id": it.sku, "quantity": it.quantity, "item_price": round(it.unit_price_cents / 100, 2)}
        for it in items
    ]
    custom_data = {
        "currency": "BRL",
        "value": round(order.grand_total_cents / 100, 2),
        "content_type": "product",
        "content_ids": [it.sku for it in items],
        "contents": contents,
        "num_items": sum(it.quantity for it in items),
        "order_id": order.number,
    }
    return await send_event(
        pixel_id=pixel_id,
        access_token=access_token,
        event_name="Purchase",
        event_id=f"purchase.{order.number}",
        event_source_url=f"{settings.site_url}/checkout/obrigado?pedido={order.number}",
        user_data=user_data,
        custom_data=custom_data,
        test_event_code=test_event_code,
    )
