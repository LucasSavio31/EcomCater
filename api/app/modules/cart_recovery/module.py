"""Módulo `cart_recovery` — captura de e-mail no checkout + lembretes por SMTP.

Fluxo:
1. No checkout, ao informar o e-mail, o front chama `POST /capture`.
2. Um cron externo chama `POST /run?token=...` periodicamente (ex.: a cada
   15 min). Cada mensagem ativa é enviada quando `agora - captura >= delay`
   e ainda não foi enviada.
3. O CTA do e-mail aponta para `GET /r/{id}` → recoloca o cookie do carrinho
   e manda para o /checkout.
4. Quando o pedido é criado (evento `order.created`), o carrinho abandonado
   do mesmo e-mail é marcado como recuperado.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.errors import ForbiddenError, NotFoundError
from app.core.module_registry import ModuleSpec, register
from app.core.ratelimit import rate_limit
from app.modules.admin.models import AdminUser
from app.modules.cart_recovery.models import AbandonedCart, RecoveryMessage

public_router = APIRouter()
admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


# --------------------------------------------------------------------- público
class CaptureIn(BaseModel):
    email: EmailStr


@public_router.post("/capture", status_code=202)
async def capture(
    body: CaptureIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("20/minute", scope="recovery"))],
    cart_token: Annotated[str | None, Cookie(alias="cart_token")] = None,
) -> dict:
    if not cart_token:
        return {"ok": False}
    from sqlalchemy.orm import selectinload

    from app.modules.cart.models import Cart

    cart = await db.scalar(
        select(Cart)
        .where(Cart.session_token == cart_token)
        .options(selectinload(Cart.items))
    )
    if not cart:
        return {"ok": False}
    from app.modules.cart.service import compute_totals

    totals = await compute_totals(db, cart)
    items_count = sum(i.quantity for i in cart.items)
    if items_count == 0:
        return {"ok": False}

    row = await db.scalar(
        select(AbandonedCart).where(
            AbandonedCart.cart_token == cart_token, AbandonedCart.recovered_at.is_(None)
        )
    )
    now = datetime.now(UTC)
    if row:
        row.email = str(body.email)
        row.total_cents = totals["grand_total_cents"]
        row.items_count = items_count
        row.cart_id = cart.id
    else:
        db.add(
            AbandonedCart(
                email=str(body.email),
                cart_id=cart.id,
                cart_token=cart_token,
                total_cents=totals["grand_total_cents"],
                items_count=items_count,
                created_at=now,
            )
        )
    await db.commit()
    return {"ok": True}


@public_router.get("/r/{rec_id}")
async def recover_link(rec_id: str, db: DbDep) -> Response:
    import uuid as _uuid

    try:
        rid = _uuid.UUID(rec_id)
    except ValueError as exc:
        raise NotFoundError("Link inválido.") from exc
    row = await db.get(AbandonedCart, rid)
    target = f"{settings.site_url.rstrip('/')}/checkout"
    resp = RedirectResponse(url=target, status_code=302)
    if row:
        resp.set_cookie(
            "cart_token",
            row.cart_token,
            max_age=60 * 60 * 24 * 30,
            httponly=False,
            samesite="lax",
        )
    return resp


# ------------------------------------------------------------- envio (cron)
async def _process_due(db: AsyncSession) -> dict:
    msgs = list(
        await db.scalars(
            select(RecoveryMessage)
            .where(RecoveryMessage.is_active.is_(True))
            .order_by(RecoveryMessage.position)
        )
    )
    if not msgs:
        return {"sent": 0}
    carts = list(
        await db.scalars(
            select(AbandonedCart).where(AbandonedCart.recovered_at.is_(None))
        )
    )
    from app.modules.newsletter.models import NewsletterSubscriber
    from app.shared import mailer

    now = datetime.now(UTC)
    sent = 0
    for ac in carts:
        idx = ac.reminders_sent
        if idx >= len(msgs):
            continue
        msg = msgs[idx]
        due = ac.created_at + timedelta(minutes=msg.delay_minutes)
        if now < due:
            continue

        sub = await db.scalar(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == ac.email)
        )
        name = (sub.name if sub and sub.name else "") or ""
        cta_url = f"{settings.public_api_url.rstrip('/')}/api/cart-recovery/r/{ac.id}"
        body = (
            (msg.body or "")
            .replace("{nome}", name)
            .replace("{link}", cta_url)
        )
        subject = (msg.subject or "").replace("{nome}", name)
        ok = await mailer.send(
            db,
            to=ac.email,
            template="cart_recovery",
            context={
                "subject": subject,
                "body": body,
                "cta_url": cta_url,
                "total": ac.total_cents,
            },
        )
        ac.reminders_sent += 1
        ac.last_email_at = now
        if ok:
            sent += 1
    await db.commit()
    return {"sent": sent}


@public_router.post("/run")
async def run_cron(db: DbDep, token: str = Query(...)) -> dict:
    if token != settings.recovery_cron_token:
        raise ForbiddenError("Token inválido.")
    return await _process_due(db)


# --------------------------------------------------------------------- admin
@admin_router.get("/carts")
async def list_carts(db: DbDep, _: AdminDep) -> list[dict]:
    rows = await db.scalars(
        select(AbandonedCart).order_by(AbandonedCart.created_at.desc()).limit(500)
    )
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "total_cents": r.total_cents,
            "items_count": r.items_count,
            "reminders_sent": r.reminders_sent,
            "recovered": r.recovered_at is not None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_email_at": r.last_email_at.isoformat() if r.last_email_at else None,
        }
        for r in rows
    ]


class MessageIn(BaseModel):
    position: int = 0
    delay_minutes: int = 60
    subject: str
    body: str = ""
    is_active: bool = True


def _msg_out(m: RecoveryMessage) -> dict:
    return {
        "id": str(m.id),
        "position": m.position,
        "delay_minutes": m.delay_minutes,
        "subject": m.subject,
        "body": m.body,
        "is_active": m.is_active,
    }


@admin_router.get("/messages")
async def list_messages(db: DbDep, _: AdminDep) -> list[dict]:
    rows = await db.scalars(select(RecoveryMessage).order_by(RecoveryMessage.position))
    return [_msg_out(m) for m in rows]


@admin_router.post("/messages", status_code=201)
async def create_message(body: MessageIn, db: DbDep, _: EditorDep) -> dict:
    m = RecoveryMessage(**body.model_dump())
    db.add(m)
    await db.flush()
    return _msg_out(m)


@admin_router.patch("/messages/{msg_id}")
async def update_message(msg_id: str, body: MessageIn, db: DbDep, _: EditorDep) -> dict:
    import uuid as _uuid

    m = await db.get(RecoveryMessage, _uuid.UUID(msg_id))
    if not m:
        raise NotFoundError("Mensagem não encontrada.")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    await db.flush()
    return _msg_out(m)


@admin_router.delete("/messages/{msg_id}", status_code=204)
async def delete_message(msg_id: str, db: DbDep, _: EditorDep) -> None:
    import uuid as _uuid

    m = await db.get(RecoveryMessage, _uuid.UUID(msg_id))
    if m:
        await db.delete(m)


@admin_router.post("/run-now")
async def run_now(db: DbDep, _: EditorDep) -> dict:
    return await _process_due(db)


async def mark_recovered(db: AsyncSession, *, email: str, order_id) -> None:
    rows = await db.scalars(
        select(AbandonedCart).where(
            AbandonedCart.email == email, AbandonedCart.recovered_at.is_(None)
        )
    )
    now = datetime.now(UTC)
    for ac in rows:
        ac.recovered_at = now
        ac.order_id = order_id


spec = register(
    ModuleSpec(
        slug="cart-recovery",
        label="Recuperação de carrinho",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        public_router=public_router,
        admin_router=admin_router,
        tags=["cart-recovery"],
    )
)
