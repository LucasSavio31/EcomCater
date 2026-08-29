"""Rotas administrativas do módulo `payment`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.payment import service
from app.modules.payment.models import Payment, PaymentWebhookEvent
from app.modules.payment.schemas import PaymentConfigIn, RefundIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
AdminRoleDep = Annotated[AdminUser, Depends(require_role("admin"))]


@router.get("/config")
async def get_config(db: DbDep, _: AdminDep) -> dict:
    cfg = await service.load_config(db)
    return {
        "active_provider": cfg.active_provider,
        "appmax_sandbox": cfg.appmax_sandbox,
        "has_token": bool(cfg.appmax_access_token),
        "methods": cfg.methods.model_dump(),
        "max_installments": cfg.max_installments,
    }


@router.put("/config")
async def update_config(body: PaymentConfigIn, db: DbDep, _: AdminRoleDep) -> dict:
    cfg = await service.save_config(db, body.model_dump(exclude_unset=True))
    return {"active_provider": cfg.active_provider, "has_token": bool(cfg.appmax_access_token)}


@router.get("/payments")
async def list_payments(db: DbDep, _: AdminDep, order_number: str | None = None) -> list[dict]:
    stmt = select(Payment).order_by(Payment.created_at.desc()).limit(200)
    rows = await db.scalars(stmt)
    return [
        {
            "id": str(p.id),
            "order_id": str(p.order_id),
            "provider": p.provider,
            "method": p.method,
            "status": p.status,
            "amount_cents": p.amount_cents,
            "provider_charge_id": p.provider_charge_id,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        }
        for p in rows
    ]


@router.post("/refund/{order_number}")
async def refund(order_number: str, body: RefundIn, db: DbDep, _: AdminRoleDep) -> dict:
    return await service.refund(db, order_number, body.amount_cents)


@router.get("/webhook-events")
async def webhook_events(db: DbDep, _: AdminDep) -> list[dict]:
    rows = await db.scalars(
        select(PaymentWebhookEvent).order_by(PaymentWebhookEvent.created_at.desc()).limit(100)
    )
    return [
        {
            "id": str(e.id),
            "provider": e.provider,
            "provider_event_id": e.provider_event_id,
            "signature_valid": e.signature_valid,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            "order_id": str(e.order_id) if e.order_id else None,
        }
        for e in rows
    ]


@router.post("/webhook-events/{event_id}/reprocess")
async def reprocess(event_id: str, db: DbDep, _: AdminRoleDep) -> dict:
    import uuid

    evt = await db.get(PaymentWebhookEvent, uuid.UUID(event_id))
    if not evt:
        from app.core.errors import NotFoundError

        raise NotFoundError("Evento não encontrado.")
    evt.processed_at = None
    await db.flush()
    return await service.handle_webhook(db, evt.provider, {}, b"", evt.payload_json or {})
