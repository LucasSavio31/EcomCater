"""Registro do módulo `newsletter` (toggleable)."""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.module_registry import ModuleSpec, register
from app.core.ratelimit import rate_limit
from app.modules.admin.models import AdminUser
from app.modules.newsletter.models import NewsletterSubscriber

public_router = APIRouter()
admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


class SubscribeIn(BaseModel):
    email: EmailStr
    name: str | None = None
    phone: str | None = None
    source: str = "home_form"


async def _maybe_send_coupon(db: AsyncSession, email: str, name: str | None) -> str | None:
    """Se houver cupom de lead configurado no tema, envia por e-mail e devolve o código."""
    from app.modules.theme.models import ThemeSettings

    theme = await db.get(ThemeSettings, 1)
    code = (getattr(theme, "lead_popup_coupon_code", None) or "").strip() if theme else ""
    if not code:
        return None
    try:
        from app.shared import mailer

        await mailer.send(
            db,
            to=email,
            template="lead_coupon",
            context={"name": name or "", "coupon": code},
        )
    except Exception:  # noqa: BLE001
        pass
    return code


@public_router.post("/subscribe", status_code=201)
async def subscribe(
    body: SubscribeIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="newsletter"))],
) -> dict:
    existing = await db.scalar(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == body.email)
    )
    send_coupon = body.source in ("popup", "lead_popup")
    coupon = await _maybe_send_coupon(db, body.email, body.name) if send_coupon else None

    if existing:
        if existing.unsubscribed_at:
            existing.unsubscribed_at = None
        if body.phone and not existing.phone:
            existing.phone = body.phone
        if coupon and not existing.coupon_code:
            existing.coupon_code = coupon
        return {"ok": True, "already": True, "coupon": coupon}

    db.add(
        NewsletterSubscriber(
            email=body.email,
            name=body.name,
            phone=body.phone,
            source=body.source,
            coupon_code=coupon,
            created_at=datetime.now(UTC),
        )
    )
    return {"ok": True, "coupon": coupon}


async def upsert_lead(
    db: AsyncSession, *, email: str, name: str | None = None, phone: str | None = None, source: str
) -> None:
    """Usado por outros módulos (ex.: comprador vira lead no checkout)."""
    if not email:
        return
    existing = await db.scalar(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    if existing:
        if name and not existing.name:
            existing.name = name
        if phone and not existing.phone:
            existing.phone = phone
        return
    db.add(
        NewsletterSubscriber(
            email=email, name=name, phone=phone, source=source, created_at=datetime.now(UTC)
        )
    )


@public_router.get("/unsubscribe")
async def unsubscribe(email: str, db: DbDep) -> dict:
    row = await db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))
    if row:
        row.unsubscribed_at = datetime.now(UTC)
    return {"ok": True}


@admin_router.get("")
async def list_subscribers(
    db: DbDep, _: Annotated[AdminUser, Depends(get_current_admin)]
) -> list[dict]:
    rows = await db.scalars(
        select(NewsletterSubscriber).order_by(NewsletterSubscriber.created_at.desc()).limit(1000)
    )
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "name": r.name,
            "phone": r.phone,
            "source": r.source,
            "coupon_code": r.coupon_code,
            "subscribed": r.unsubscribed_at is None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


spec = register(
    ModuleSpec(
        slug="newsletter",
        label="Newsletter",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        public_router=public_router,
        admin_router=admin_router,
        tags=["newsletter"],
    )
)
