"""Subscribers de analytics server-side:
 - pedido pago  → Meta Conversions API (`Purchase`)
 - pedido estornado → GA4 Measurement Protocol (`refund`)

Os demais eventos de e-commerce saem pelo `dataLayer` no navegador.
"""
from __future__ import annotations

import hashlib
import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.analytics import capi, ga4_mp, service
from app.modules.orders.models import Order

logger = logging.getLogger("analytics.events")


@on("order.paid")
async def _capi_purchase(payload: dict) -> None:
    order_id = payload.get("order_id")
    if not order_id:
        return
    async with SessionLocal() as db:
        cfg = await service.get_settings(db)
        if not (cfg.meta_capi_enabled and cfg.meta_capi_access_token and cfg.meta_pixel_id):
            return
        order = await db.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        if not order:
            return
        mkt = order.marketing_json or {}
        await capi.send_purchase(
            pixel_id=cfg.meta_pixel_id,
            access_token=cfg.meta_capi_access_token,
            order=order,
            items=list(order.items),
            test_event_code=cfg.meta_test_event_code,
            client_ip=mkt.get("client_ip"),
            client_ua=mkt.get("client_user_agent"),
            fbp=mkt.get("fbp"),
            fbc=mkt.get("fbc"),
        )


@on("order.status_changed")
async def _ga4_refund(payload: dict) -> None:
    """Pedido estornado no painel → GA4 `refund` via Measurement Protocol.

    Reembolso TOTAL (o sistema não tem estorno parcial de item). Nunca é
    tratado como nova conversão — é o evento `refund` do GA4.
    """
    if payload.get("status") != "refunded":
        return
    order_id = payload.get("order_id")
    if not order_id:
        return
    async with SessionLocal() as db:
        cfg = await service.get_settings(db)
        if not (cfg.ga4_enabled and cfg.ga4_measurement_id and cfg.ga4_api_secret):
            return
        order = await db.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        if not order:
            return
        mkt = order.marketing_json or {}
        # client_id do GA4 capturado no checkout; senão um id determinístico
        # (o refund entra no GA4 mesmo sem casar com a sessão original).
        client_id = mkt.get("ga_client_id") or (
            f"{int(hashlib.sha1(order.number.encode()).hexdigest()[:8], 16)}.{int(time.time())}"
        )
        await ga4_mp.send_event(
            measurement_id=cfg.ga4_measurement_id,
            api_secret=cfg.ga4_api_secret,
            client_id=client_id,
            name="refund",
            params=ga4_mp.refund_params(order, list(order.items)),
        )
