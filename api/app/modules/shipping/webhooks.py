"""Webhook de rastreio do provedor de frete → atualiza status do pedido."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ForbiddenError
from app.modules.shipping import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/melhor-envio")
async def melhor_envio_webhook(request: Request, db: DbDep, token: str | None = None) -> dict:
    cfg = await service.load_config(db)
    if cfg.webhook_token and token != cfg.webhook_token:
        raise ForbiddenError("Token de webhook inválido.")
    raw = await request.body()
    body = await request.json()
    return await service.handle_tracking_webhook(db, dict(request.headers), raw, body)
