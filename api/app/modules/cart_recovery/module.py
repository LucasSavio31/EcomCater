"""Módulo `cart_recovery` — captura de e-mail no checkout + lembretes por SMTP.

Fluxo:
1. No checkout, ao informar o e-mail, o front chama `POST /capture`.
2. Um cron externo chama `POST /run?token=...` periodicamente (ex.: a cada
   15 min). Cada mensagem ativa é enviada quando `agora - captura >= delay`
   e ainda não foi enviada.
3. O CTA do e-mail aponta para `GET /r/{id}` → recoloca o cookie do carrinho
   e manda para o /carrinho.
4. Quando o pedido é criado (evento `order.created`), o carrinho abandonado
   do mesmo e-mail é marcado como recuperado.
"""
from __future__ import annotations

import re
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
    # volta para o CARRINHO (o cliente revê os itens antes de finalizar)
    target = f"{settings.site_url.rstrip('/')}/carrinho"
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
async def _resolve_name(db: AsyncSession, email: str) -> str:
    """Primeiro nome do cliente: lead → conta → último pedido → vazio."""
    from app.modules.newsletter.models import NewsletterSubscriber

    sub = await db.scalar(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    full = (sub.name if sub and sub.name else "") or ""
    if not full.strip():
        from app.modules.customers.models import User

        u = await db.scalar(select(User).where(User.email == email))
        full = (u.full_name if u and u.full_name else "") or ""
    if not full.strip():
        from app.modules.orders.models import Order

        o = await db.scalar(
            select(Order).where(Order.email == email).order_by(Order.placed_at.desc())
        )
        if o and o.shipping_address_json:
            full = (o.shipping_address_json.get("recipient_name") or "").strip()
    return full.split()[0] if full.strip() else ""


def _fill(text: str, *, name: str, link: str) -> str:
    """Troca {link} e {nome}. Sem nome, remove o placeholder e a vírgula/espaço
    logo depois (evita '‚ você esqueceu...' e 'Olá , notamos...')."""
    text = (text or "").replace("{link}", link)
    if name:
        return text.replace("{nome}", name)
    return re.sub(r"\{nome\}\s*,?\s*", "", text).strip()


async def _cart_lines(db: AsyncSession, cart_id) -> tuple[list[dict], int]:
    """Resumo do carrinho: [{name, variant, qty, unit_cents, line_cents}], total."""
    if not cart_id:
        return [], 0
    from sqlalchemy.orm import selectinload

    from app.modules.cart.models import Cart
    from app.modules.products.models import Product, ProductVariant

    cart = await db.scalar(
        select(Cart).where(Cart.id == cart_id).options(selectinload(Cart.items))
    )
    if not cart or not cart.items:
        return [], 0
    lines: list[dict] = []
    total = 0
    for it in cart.items:
        prod = await db.get(Product, it.product_id)
        var = await db.scalar(
            select(ProductVariant)
            .where(ProductVariant.id == it.variant_id)
            .options(selectinload(ProductVariant.option_values))
        )
        vlabel = (
            " / ".join(ov.value for ov in var.option_values)
            if var and var.option_values
            else None
        )
        line = it.unit_price_cents * it.quantity
        total += line
        lines.append(
            {
                "name": prod.name if prod else "Item",
                "variant": vlabel,
                "qty": it.quantity,
                "unit_cents": it.unit_price_cents,
                "line_cents": line,
            }
        )
    return lines, total


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

        name = await _resolve_name(db, ac.email)
        lines, total = await _cart_lines(db, ac.cart_id)
        cta_url = f"{settings.public_api_url.rstrip('/')}/api/cart-recovery/r/{ac.id}"
        ok = await mailer.send(
            db,
            to=ac.email,
            template="cart_recovery",
            context={
                "subject": _fill(msg.subject, name=name, link=cta_url),
                "body": _fill(msg.body, name=name, link=cta_url),
                "cta_url": cta_url,
                "items": lines,
                "total_cents": total or ac.total_cents,
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
@admin_router.post("/carts/delete")
async def delete_carts(db: DbDep, _: EditorDep, ids: list[str] = Body(..., embed=True)) -> dict:
    import uuid as _uuid

    uids = []
    for i in ids:
        try:
            uids.append(_uuid.UUID(i))
        except ValueError:
            continue
    if uids:
        await db.execute(AbandonedCart.__table__.delete().where(AbandonedCart.id.in_(uids)))
    return {"ok": True, "deleted": len(uids)}


@admin_router.get("/stats")
async def recovery_stats(db: DbDep, _: AdminDep) -> dict:
    """Métricas de recuperação de carrinho (histórico completo).

    O rastreio já existe: o e-mail é capturado no checkout (`/capture`) e
    amarrado ao carrinho pelo cookie `cart_token`; quando um pedido é criado
    com o mesmo e-mail (`order.created` → `mark_recovered`), o carrinho é
    marcado como recuperado.
    """
    from sqlalchemy import func

    total = int(
        await db.scalar(select(func.count()).select_from(AbandonedCart)) or 0
    )
    recovered = int(
        await db.scalar(
            select(func.count())
            .select_from(AbandonedCart)
            .where(AbandonedCart.recovered_at.is_not(None))
        )
        or 0
    )
    # recuperados DEPOIS de pelo menos um lembrete (mérito da automação)
    recovered_after_email = int(
        await db.scalar(
            select(func.count())
            .select_from(AbandonedCart)
            .where(
                AbandonedCart.recovered_at.is_not(None),
                AbandonedCart.reminders_sent > 0,
            )
        )
        or 0
    )
    reminded = int(
        await db.scalar(
            select(func.count())
            .select_from(AbandonedCart)
            .where(AbandonedCart.reminders_sent > 0)
        )
        or 0
    )
    recovered_revenue = int(
        await db.scalar(
            select(func.coalesce(func.sum(AbandonedCart.total_cents), 0)).where(
                AbandonedCart.recovered_at.is_not(None)
            )
        )
        or 0
    )
    abandoned = total - recovered
    return {
        "total": total,
        "recovered": recovered,
        "abandoned": abandoned,
        "reminded": reminded,
        "recovered_after_email": recovered_after_email,
        "recovery_rate_pct": round(recovered / total * 100, 1) if total else 0.0,
        "email_recovery_rate_pct": (
            round(recovered_after_email / reminded * 100, 1) if reminded else 0.0
        ),
        "recovered_revenue_cents": recovered_revenue,
    }


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


@admin_router.post("/carts/send")
async def send_to_carts(
    db: DbDep, _: EditorDep, ids: list[str] = Body(..., embed=True)
) -> dict:
    """Envia AGORA um e-mail de recuperação para os carrinhos escolhidos,
    ignorando o `delay`. Se o carrinho já recebeu todas as mensagens, reenvia
    a última. Não envia para carrinho já recuperado."""
    import uuid as _uuid

    from app.shared import mailer

    msgs = list(
        await db.scalars(
            select(RecoveryMessage)
            .where(RecoveryMessage.is_active.is_(True))
            .order_by(RecoveryMessage.position)
        )
    )
    if not msgs:
        return {"sent": 0, "skipped": 0, "reason": "nenhuma mensagem ativa cadastrada"}

    uids = []
    for i in ids:
        try:
            uids.append(_uuid.UUID(i))
        except ValueError:
            continue
    if not uids:
        return {"sent": 0, "skipped": 0}

    carts = list(await db.scalars(select(AbandonedCart).where(AbandonedCart.id.in_(uids))))
    now = datetime.now(UTC)
    sent = skipped = 0
    for ac in carts:
        if ac.recovered_at is not None:
            skipped += 1
            continue
        msg = msgs[min(ac.reminders_sent, len(msgs) - 1)]
        name = await _resolve_name(db, ac.email)
        lines, total = await _cart_lines(db, ac.cart_id)
        cta_url = f"{settings.public_api_url.rstrip('/')}/api/cart-recovery/r/{ac.id}"
        ok = await mailer.send(
            db,
            to=ac.email,
            template="cart_recovery",
            context={
                "subject": _fill(msg.subject, name=name, link=cta_url),
                "body": _fill(msg.body, name=name, link=cta_url),
                "cta_url": cta_url,
                "items": lines,
                "total_cents": total or ac.total_cents,
            },
        )
        ac.last_email_at = now
        if ac.reminders_sent < len(msgs):
            ac.reminders_sent += 1
        if ok:
            sent += 1
        else:
            skipped += 1
    await db.commit()
    return {"sent": sent, "skipped": skipped}


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
