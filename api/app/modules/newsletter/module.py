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
    source: str = "home_form"


@public_router.post("/subscribe", status_code=201)
async def subscribe(
    body: SubscribeIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("10/minute", scope="newsletter"))],
) -> dict:
    existing = await db.scalar(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == body.email)
    )
    if existing:
        if existing.unsubscribed_at:
            existing.unsubscribed_at = None
        return {"ok": True, "already": True}
    db.add(
        NewsletterSubscriber(
            email=body.email, name=body.name, source=body.source, created_at=datetime.now(UTC)
        )
    )
    return {"ok": True}


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
            "source": r.source,
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
