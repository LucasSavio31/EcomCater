"""Subscriber: pedido pago → Meta Conversions API (`Purchase`)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.analytics import capi, service
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
        await capi.send_purchase(
            pixel_id=cfg.meta_pixel_id,
            access_token=cfg.meta_capi_access_token,
            order=order,
            items=list(order.items),
            test_event_code=cfg.meta_test_event_code,
        )
