"""Alimenta o livro-caixa a partir dos eventos de pedido.

Roda no event-bus in-process; cada handler abre a própria sessão. Nunca
propaga erro (métrica não pode quebrar o fluxo do pedido).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.financial import service
from app.modules.orders.models import Order

logger = logging.getLogger("financial.events")


async def _load(db, order_id: str) -> Order | None:
    return await db.scalar(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )


async def _record(order_id: str, kind: str) -> None:
    try:
        async with SessionLocal() as db:
            order = await _load(db, order_id)
            if not order:
                return
            await service.record(db, kind=kind, order=order)
            await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("livro-caixa: falha ao registrar '%s' do pedido %s", kind, order_id)


@on("order.created")
async def _on_created(payload: dict) -> None:
    await _record(payload["order_id"], "placed")


@on("order.paid")
async def _on_paid(payload: dict) -> None:
    await _record(payload["order_id"], "paid")


@on("order.status_changed")
async def _on_status(payload: dict) -> None:
    st = payload.get("status")
    if st == "refunded":
        await _record(payload["order_id"], "refunded")
    elif st == "canceled":
        await _record(payload["order_id"], "canceled")
