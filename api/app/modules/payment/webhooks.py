"""Webhook de confirmação de pagamento (sem auth; valida assinatura no service)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.payment import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/{provider}")
async def payment_webhook(provider: str, request: Request, db: DbDep) -> dict:
    raw = await request.body()
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    return await service.handle_webhook(db, provider, dict(request.headers), raw, body)
