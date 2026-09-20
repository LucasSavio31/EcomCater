"""Cria notificações a partir de eventos de pedido -- "nova venda" (pedido
criado), "novo envio" (pedido marcado como enviado), "venda paga" e
"devolução entregue" (as duas últimas também disparam som no admin, ver
`ThemeSettings.sound_sale_enabled`/`sound_return_enabled`).

Roda no event-bus in-process; cada handler abre a própria sessão. Nunca
propaga erro (uma notificação falhando não pode derrubar o fluxo do pedido).
"""
from __future__ import annotations

import logging

from app.core.database import SessionLocal
from app.core.events import on
from app.modules.notifications import service

logger = logging.getLogger("notifications.events")


def _brl(cents: int) -> str:
    return f"R$ {cents / 100:.2f}".replace(".", ",")


@on("order.created")
async def _on_order_created(payload: dict) -> None:
    order_id = payload.get("order_id")
    number = payload.get("number")
    if not order_id or not number:
        return
    async with SessionLocal() as db:
        try:
            from app.modules.orders.models import Order

            order = await db.get(Order, order_id)
            if not order:
                return
            addr = order.shipping_address_json or {}
            who = addr.get("recipient_name") or order.email
            await service.create(
                db,
                type="order_created",
                title=f"Nova venda: pedido {number}",
                message=f"{who} · {_brl(order.grand_total_cents)}",
                link_path=f"/pedidos/{number}",
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("falha ao criar notificação de venda (order_id=%s)", order_id)
            await db.rollback()


@on("order.status_changed")
async def _on_order_status_changed(payload: dict) -> None:
    if payload.get("status") != "shipped":
        return
    order_id = payload.get("order_id")
    if not order_id:
        return
    async with SessionLocal() as db:
        try:
            from app.modules.orders.models import Order

            order = await db.get(Order, order_id)
            if not order:
                return
            addr = order.shipping_address_json or {}
            who = addr.get("recipient_name") or order.email
            svc = order.shipping_service_json or {}
            tracking = svc.get("tracking_code")
            await service.create(
                db,
                type="order_shipped",
                title=f"Novo envio: pedido {order.number}",
                message=f"{who}" + (f" · rastreio {tracking}" if tracking else ""),
                link_path=f"/pedidos/{order.number}",
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("falha ao criar notificação de envio (order_id=%s)", order_id)
            await db.rollback()


@on("order.paid")
async def _on_order_paid(payload: dict) -> None:
    order_id = payload.get("order_id")
    number = payload.get("number")
    if not order_id or not number:
        return
    async with SessionLocal() as db:
        try:
            from app.modules.orders.models import Order

            order = await db.get(Order, order_id)
            if not order:
                return
            addr = order.shipping_address_json or {}
            who = addr.get("recipient_name") or order.email
            await service.create(
                db,
                type="order_paid",
                title=f"Venda paga: pedido {number}",
                message=f"{who} · {_brl(order.grand_total_cents)}",
                link_path=f"/pedidos/{number}",
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("falha ao criar notificação de pagamento (order_id=%s)", order_id)
            await db.rollback()


@on("order.status_changed")
async def _on_order_returned(payload: dict) -> None:
    if payload.get("status") != "returned":
        return
    order_id = payload.get("order_id")
    if not order_id:
        return
    async with SessionLocal() as db:
        try:
            from app.modules.orders.models import Order

            order = await db.get(Order, order_id)
            if not order:
                return
            addr = order.shipping_address_json or {}
            who = addr.get("recipient_name") or order.email
            await service.create(
                db,
                type="order_returned",
                title=f"Devolução entregue: pedido {order.number}",
                message=who,
                link_path=f"/pedidos/{order.number}",
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("falha ao criar notificação de devolução (order_id=%s)", order_id)
            await db.rollback()
