"""Dispara webhook (formato WooCommerce) pros apps assinados -- direção
"loja -> ERP" (Bling etc., via o app WooCommerce deles).

Roda no event-bus in-process; cada handler abre a própria sessão. Nunca
propaga erro (uma entrega falhando não pode derrubar o fluxo do pedido) --
fica só logado (ver `service.deliver`).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.orders.models import Order
from app.modules.woocommerce import service

logger = logging.getLogger("woocommerce.events")


async def _load_order(db, order_id: str) -> Order | None:
    return await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )


async def _handle(topic: str, payload: dict) -> None:
    order_id = payload.get("order_id")
    if not order_id:
        return
    async with SessionLocal() as db:
        try:
            order = await _load_order(db, order_id)
            if order:
                await service.deliver(db, topic=topic, order=order)
        except Exception:  # noqa: BLE001 - nunca deixa o handler derrubar o evento
            logger.exception("falha ao entregar webhook %s (order_id=%s)", topic, order_id)


@on("order.created")
async def _on_created(payload: dict) -> None:
    await _handle("order.created", payload)


# `order.status_changed` já dispara pra TODA transição, inclusive virar
# "paid" -- não assina `order.paid` também, ou entregaria o webhook em
# dobro pra essa transição especificamente (os dois eventos são emitidos
# juntos, ver `orders.service.transition`).
@on("order.status_changed")
async def _on_status_changed(payload: dict) -> None:
    await _handle("order.updated", payload)
