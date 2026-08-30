"""Subscribers de eventos de pedido → e-mails transacionais.

Cada handler abre a própria sessão (o event bus é in-process e desacoplado da
request). Falha de e-mail é logada, nunca propaga.

Regra: o LOJISTA só recebe e-mail no evento de pedido criado. Todo o resto
(pagamento, separação, envio, trânsito, entrega, cancelamento, reembolso) vai
apenas para o cliente.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.events import on
from app.modules.admin.models import StoreSettings
from app.modules.orders.models import Order
from app.modules.payment.models import Payment
from app.shared import mailer

logger = logging.getLogger("orders.events")


async def _order(db, order_id: str) -> Order | None:
    return await db.scalar(
        select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
    )


async def _store_name(db) -> str:
    row = await db.get(StoreSettings, 1)
    return (row.store_name if row and row.store_name else None) or "nossa loja"


def _tracking(order: Order) -> str | None:
    return (order.shipping_service_json or {}).get("tracking_code")


def _tracking_url(order: Order) -> str | None:
    code = _tracking(order)
    if not code:
        return None
    svc = order.shipping_service_json or {}
    return svc.get("tracking_url") or f"https://www.linkcorreios.com.br/?id={code}"


@on("order.created")
async def _on_created(payload: dict) -> None:
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        pay = await db.scalar(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )
        # Cliente
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
        # Marca carrinho abandonado como recuperado
        try:
            from app.modules.cart_recovery.module import mark_recovered

            await mark_recovered(db, email=order.email, order_id=order.id)
        except Exception:  # noqa: BLE001
            logger.exception("falha ao marcar carrinho recuperado de %s", order.email)

        # Comprador entra na lista de leads (para campanhas)
        try:
            from app.modules.newsletter.module import upsert_lead

            addr = order.shipping_address_json or {}
            await upsert_lead(
                db,
                email=order.email,
                name=addr.get("recipient_name"),
                phone=addr.get("phone"),
                source="checkout",
            )
        except Exception:  # noqa: BLE001
            logger.exception("falha ao registrar lead do comprador %s", order.email)

        # Lojista (ÚNICO e-mail que o admin recebe)
        try:
            admin_to = await mailer.admin_notify_email(db)
            items = [
                f"{i.quantity}x {i.name}" + (f" ({i.variant_label})" if i.variant_label else "")
                for i in order.items
            ]
            from app.modules.orders.service import _customer_name

            await mailer.send(
                db,
                to=admin_to,
                template="admin_order_created",
                order_id=str(order.id),
                context={
                    "number": order.number,
                    "total_cents": order.grand_total_cents,
                    "email": order.email,
                    "customer_name": _customer_name(order),
                    "items": items,
                    "admin_url": f"{settings.admin_url.rstrip('/')}/pedidos/{order.number}",
                },
            )
        except Exception:  # noqa: BLE001
            logger.exception("falha ao notificar lojista do pedido %s", order.number)
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


# status do pedido -> template do e-mail para o CLIENTE
_STATUS_TEMPLATE = {
    "paid": "payment_confirmed",
    "processing": "order_processing",
    "shipped": "order_shipped",
    "in_transit": "order_in_transit",  # sub-status vindo do rastreio
    "delivered": "order_delivered",
    "canceled": "order_canceled",
    "refunded": "order_refunded",
}


@on("order.status_changed")
async def _on_status(payload: dict) -> None:
    status = payload.get("status")
    template = _STATUS_TEMPLATE.get(status)
    if not template:
        return
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        await mailer.send(
            db,
            to=order.email,
            template=template,
            order_id=str(order.id),
            context={
                "number": order.number,
                "tracking": _tracking(order),
                "tracking_url": _tracking_url(order),
                "store_name": await _store_name(db),
                "review_url": f"{settings.site_url.rstrip('/')}/minha-conta/pedidos",
            },
        )
        await db.commit()
