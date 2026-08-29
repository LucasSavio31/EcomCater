"""Subscribers de eventos de pedido → e-mails transacionais.

Cada handler abre a própria sessão (o event bus é in-process e desacoplado da
request). Falha de e-mail é logada, nunca propaga.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.orders.models import Order
from app.modules.payment.models import Payment
from app.shared import mailer

logger = logging.getLogger("orders.events")


async def _order(db, order_id: str) -> Order | None:
    return await db.scalar(
        select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
    )


@on("order.created")
async def _on_created(payload: dict) -> None:
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        pay = await db.scalar(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )
        await mailer.send(
            db,
            to=order.email,
            template="order_created",
            order_id=str(order.id),
            context={
                "number": order.number,
                "total_cents": order.grand_total_cents,
                "pix_qr": pay.pix_qr_code if pay else None,
                "boleto_url": pay.boleto_url if pay else None,
            },
        )
        await db.commit()


@on("order.paid")
async def _on_paid(payload: dict) -> None:
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        await mailer.send(
            db, to=order.email, template="payment_confirmed",
            order_id=str(order.id), context={"number": order.number},
        )
        await db.commit()


@on("order.status_changed")
async def _on_status(payload: dict) -> None:
    status = payload.get("status")
    template = {"shipped": "order_shipped", "delivered": "order_delivered", "canceled": "payment_failed"}.get(status)
    if not template:
        return
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        await mailer.send(
            db, to=order.email, template=template,
            order_id=str(order.id),
            context={"number": order.number, "tracking": (order.shipping_service_json or {}).get("tracking_code")},
        )
        await db.commit()
