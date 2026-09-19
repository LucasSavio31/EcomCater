"""Webhook de rastreio do provedor de frete → atualiza status do pedido."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ForbiddenError
from app.modules.shipping import service

logger = logging.getLogger("shipping.webhooks")

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/melhor-envio")
async def melhor_envio_webhook(request: Request, db: DbDep, token: str | None = None) -> dict:
    cfg = await service.load_config(db)
    # Sem token configurado: RECUSA (falha fechada) -- sem isso, qualquer um
    # poderia forjar atualização de rastreio/entrega de um pedido.
    if not cfg.webhook_token:
        logger.warning(
            "webhook Melhor Envio recusado: nenhum webhook_token configurado (menu Frete)"
        )
        raise ForbiddenError("Webhook não configurado.")
    if token != cfg.webhook_token:
        raise ForbiddenError("Token de webhook inválido.")
    raw = await request.body()
    body = await request.json()
    return await service.handle_tracking_webhook(db, dict(request.headers), raw, body)


@router.post("/frenet")
async def frenet_webhook(request: Request, db: DbDep) -> dict:
    """A Frenet não assina o webhook -- a verificação é por um header
    customizado (nome/valor escolhidos pelo lojista), conferido dentro de
    `FrenetProvider.verify_webhook` (falha fechada, igual ao token do ME)."""
    raw = await request.body()
    body = await request.json()
    return await service.handle_frenet_tracking_webhook(db, dict(request.headers), raw, body)
