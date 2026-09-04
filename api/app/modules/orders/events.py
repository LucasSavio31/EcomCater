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
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.events import on
from app.modules.admin.models import StoreSettings
from app.modules.orders.models import Order
from app.modules.payment.models import Payment
from app.shared import mailer

logger = logging.getLogger("orders.events")


async def _order(db, order_id: str) -> Order | None:
    # `items` é carregado junto: os handlers rodam fora do contexto de request
    # e o acesso lazy a relationship em sessão async estoura MissingGreenlet.
    return await db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
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


_PAY_LABELS = {
    "pix": "Pix", "boleto": "Boleto", "credit_card": "Cartão de crédito",
    "card": "Cartão de crédito", "debit_card": "Cartão de débito",
}


def _order_ctx(order: Order, pay: Payment | None) -> dict:
    """Contexto rico (itens + totais + pagamento + envio + endereço) para os
    e-mails de pedido — cliente e lojista compartilham."""
    addr = order.shipping_address_json or {}
    svc = order.shipping_service_json or {}
    eta = (
        svc.get("delivery_time")
        or svc.get("delivery_range", {}).get("max")
        or svc.get("custom_delivery_time")
    )
    line = f"{addr.get('street', '')}, {addr.get('number', '')}".strip(", ")
    if addr.get("complement"):
        line += f" - {addr['complement']}"
    return {
        "number": order.number,
        "items": [
            {
                "name": i.name,
                "qty": i.quantity,
                "variant": i.variant_label,
                "line_cents": (i.unit_price_cents or 0) * i.quantity,
            }
            for i in order.items
        ],
        "items_total_cents": order.items_total_cents,
        "discount_cents": order.discount_cents,
        "shipping_cents": order.shipping_cents,
        "total_cents": order.grand_total_cents,
        "coupon_code": order.coupon_code,
        "payment_method": _PAY_LABELS.get(pay.method, pay.method) if pay else None,
        "installments": pay.installments if pay else None,
        "pix_qr": pay.pix_qr_code if pay else None,
        "boleto_url": pay.boleto_url if pay else None,
        "shipping_method": order.shipping_method or svc.get("name") or svc.get("service"),
        "shipping_eta": eta,
        "tracking_code": svc.get("tracking_code"),
        "address": {
            "recipient": addr.get("recipient_name") or order.email,
            "line": line,
            "district": addr.get("district"),
            "city": addr.get("city"),
            "state": (addr.get("state") or "").upper(),
            "zip": addr.get("zip"),
        }
        if addr
        else None,
    }


async def _send_account_access(db, order: Order) -> None:
    """Manda o e-mail com os dados de acesso quando o comprador tem uma conta
    cujo login é e-mail + CPF (conta criada no checkout, sem senha própria)."""
    if not order.user_id:
        return
    from app.core.security import verify_password
    from app.modules.admin.models import StoreSettings
    from app.modules.customers.models import User

    user = await db.get(User, order.user_id)
    if not user or not user.email or not user.cpf:
        return
    # só se o CPF ainda é a senha (não trocou por uma própria)
    if not verify_password(user.cpf, user.password_hash):
        return
    store = await db.get(StoreSettings, 1)
    cpf = user.cpf
    masked = f"{cpf[:3]}.***.***-{cpf[-2:]}" if len(cpf) == 11 else None
    await mailer.send(
        db,
        to=user.email,
        template="account_access",
        context={
            "store_name": (store.store_name if store else None) or "nossa loja",
            "email": user.email,
            "cpf_masked": masked,
            "login_url": f"{settings.site_url.rstrip('/')}/minha-conta",
        },
    )


@on("order.created")
async def _on_created(payload: dict) -> None:
    """Finalização "por baixo dos panos": e-mails + registros pós-pedido. Roda
    em BackgroundTask (o cliente já viu "pedido recebido"). Cada passo é isolado;
    o que falhar é registrado em `order.processing_error` e avisado por e-mail
    ao lojista — o pedido em si já está gravado e íntegro."""
    failures: list[str] = []
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        pay = await db.scalar(
            select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
        )
        ctx = _order_ctx(order, pay)
        ctx["status_label"] = _STATUS_LABELS.get(order.status, "Aguardando pagamento")

        from app.modules.orders.service import _customer_name

        async def _confirm_email() -> None:
            ok = await mailer.send(
                db, to=order.email, template="order_created",
                order_id=str(order.id), context=ctx,
            )
            if not ok:
                raise RuntimeError("mailer retornou status != sent")

        async def _mark_recovered() -> None:
            from app.modules.cart_recovery.module import mark_recovered

            await mark_recovered(db, email=order.email, order_id=order.id)

        async def _lead() -> None:
            from app.modules.newsletter.module import upsert_lead

            addr = order.shipping_address_json or {}
            await upsert_lead(
                db, email=order.email, name=addr.get("recipient_name"),
                phone=addr.get("phone"), source="checkout",
            )

        async def _admin_email() -> None:
            admin_to = await mailer.order_notify_email(db)
            await mailer.send(
                db, to=admin_to, template="admin_order_created", order_id=str(order.id),
                context={
                    **ctx,
                    "email": order.email,
                    "customer_name": _customer_name(order),
                    "customer_phone": (order.shipping_address_json or {}).get("phone"),
                    "admin_url": f"{settings.admin_url.rstrip('/')}/pedidos/{order.number}",
                },
            )

        steps = [
            ("e-mail de confirmação ao cliente", _confirm_email),
            ("e-mail de dados de acesso", lambda: _send_account_access(db, order)),
            ("marcação de carrinho recuperado", _mark_recovered),
            ("registro de lead", _lead),
            ("aviso de novo pedido ao lojista", _admin_email),
        ]
        for label, step in steps:
            try:
                await step()
            except Exception as exc:  # noqa: BLE001
                logger.exception("order.created [%s] falhou (pedido %s)", label, order.number)
                failures.append(f"{label}: {type(exc).__name__}: {exc}")

        if failures:
            order.processing_error = " | ".join(failures)[:2000]
        await db.commit()

    if failures:
        await _alert_store_owner(payload["order_id"], payload.get("number"), failures)


async def _alert_store_owner(order_id: str, number: str | None, failures: list[str]) -> None:
    """E-mail de erro ao lojista (sessão própria, best-effort)."""
    try:
        async with SessionLocal() as db:
            admin_to = await mailer.order_notify_email(db)
            body = "".join(f"<li>{f}</li>" for f in failures)
            await mailer.send(
                db,
                to=admin_to,
                template="admin_order_error",
                order_id=order_id,
                context={
                    "number": number or "",
                    "failures_html": body,
                    "admin_url": f"{settings.admin_url.rstrip('/')}/pedidos/{number or ''}",
                },
            )
    except Exception:  # noqa: BLE001
        logger.exception("falha ao avisar lojista do erro de finalização (%s)", number)


async def _latest_payment(db, order: Order) -> Payment | None:
    return await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )


@on("order.paid")
async def _on_paid(payload: dict) -> None:
    async with SessionLocal() as db:
        order = await _order(db, payload["order_id"])
        if not order:
            return
        ctx = _order_ctx(order, await _latest_payment(db, order))
        ctx["status_label"] = _STATUS_LABELS.get("paid", "Pago")

        # anexa a fatura em PDF (best-effort — falha não bloqueia o e-mail)
        attachments = None
        try:
            from app.modules.orders.invoice import build_invoice_pdf

            pdf = await build_invoice_pdf(db, order)
            attachments = [(f"fatura-{order.number}.pdf", pdf, "application", "pdf")]
        except Exception:  # noqa: BLE001
            logger.exception("falha ao gerar a fatura PDF do pedido %s", order.number)

        await mailer.send(
            db, to=order.email, template="payment_confirmed",
            order_id=str(order.id), context=ctx, attachments=attachments,
        )
        await db.commit()


# status do pedido -> template do e-mail para o CLIENTE.
# "paid" NÃO está aqui: o e-mail de pagamento confirmado (com a fatura em PDF)
# sai do handler `order.paid`, pra não duplicar.
_STATUS_TEMPLATE = {
    "processing": "order_processing",
    "tracking_available": "order_tracking_available",
    "shipped": "order_shipped",
    "in_transit": "order_in_transit",  # sub-status vindo do rastreio
    "delivered": "order_delivered",
    "canceled": "order_canceled",
    "refunded": "order_refunded",
}

# rótulo humano do status, mostrado em TODO e-mail de pedido
_STATUS_LABELS = {
    "pending_payment": "Aguardando pagamento",
    "paid": "Pago",
    "processing": "Em separação",
    "tracking_available": "Rastreio disponível",
    "shipped": "Enviado",
    "in_transit": "Em trânsito",
    "delivered": "Entregue",
    "canceled": "Cancelado",
    "refunded": "Reembolsado",
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
        ctx = _order_ctx(order, await _latest_payment(db, order))
        ctx.update(
            tracking=_tracking(order),
            tracking_url=_tracking_url(order),
            store_name=await _store_name(db),
            review_url=f"{settings.site_url.rstrip('/')}/minha-conta/pedidos",
            status_label=_STATUS_LABELS.get(status, status),
        )
        await mailer.send(
            db, to=order.email, template=template, order_id=str(order.id), context=ctx
        )
        await db.commit()
