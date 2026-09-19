"""Rotas administrativas do módulo `payment`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.payment import service
from app.modules.payment.models import Payment, PaymentWebhookEvent
from app.modules.payment.schemas import MethodProvidersIn, ProviderConfigIn, RefundIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
AdminRoleDep = Annotated[AdminUser, Depends(require_role("admin"))]


def _config_out(cfg) -> dict:
    base = settings.public_api_url.rstrip("/")
    providers_out: dict = {}
    for slug, entry in cfg.providers.items():
        out: dict = {"enabled": entry.enabled}
        if slug == "appmax":
            out["sandbox"] = entry.config.get("sandbox", True)
            out["has_token"] = bool(entry.config.get("access_token"))
            out["has_webhook_secret"] = bool(entry.config.get("webhook_secret"))
        providers_out[slug] = out
    return {
        "providers": providers_out,
        "method_providers": cfg.method_providers,
        "max_installments": cfg.max_installments,
        # URL que o lojista cadastra no painel de cada gateway ativo
        "webhook_urls": {
            slug: f"{base}/api/webhooks/payment/{slug}"
            for slug, entry in cfg.providers.items()
            if entry.enabled
        },
    }


@router.get("/config")
async def get_config(db: DbDep, _: AdminDep) -> dict:
    return _config_out(await service.load_config(db))


@router.put("/config/providers/{slug}")
async def update_provider(slug: str, body: ProviderConfigIn, db: DbDep, _: AdminRoleDep) -> dict:
    cfg = await service.update_provider(db, slug, enabled=body.enabled, config_patch=body.config or {})
    return _config_out(cfg)


@router.put("/config/method-providers")
async def update_method_providers(body: MethodProvidersIn, db: DbDep, _: AdminRoleDep) -> dict:
    mapping = {
        "credit_card": body.credit_card,
        "pix": body.pix,
        "boleto": body.boleto,
    }
    cfg = await service.update_method_providers(db, mapping, body.max_installments)
    return _config_out(cfg)


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
async def refund(
    order_number: str, body: RefundIn, db: DbDep, _: AdminRoleDep, background: BackgroundTasks
) -> dict:
    return await service.refund(db, order_number, body.amount_cents, background=background)


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
async def reprocess(
    event_id: str, db: DbDep, _: AdminRoleDep, background: BackgroundTasks
) -> dict:
    import uuid

    evt = await db.get(PaymentWebhookEvent, uuid.UUID(event_id))
    if not evt:
        from app.core.errors import NotFoundError

        raise NotFoundError("Evento não encontrado.")
    evt.processed_at = None
    await db.flush()
    return await service.handle_webhook(
        db, evt.provider, {}, b"", evt.payload_json or {}, background=background
    )
