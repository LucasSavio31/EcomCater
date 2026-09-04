"""Webhook de confirmação de pagamento (sem auth; valida assinatura no service)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.payment import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/{provider}")
async def payment_webhook(
    provider: str, request: Request, db: DbDep, background: BackgroundTasks
) -> dict:
    """Valida, persiste e aplica o evento; responde rápido. E-mail/fatura (o
    trabalho pesado) roda DEPOIS da resposta, pra não arriscar o gateway
    considerar o webhook lento/falho e reenviar."""
    raw = await request.body()
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    return await service.handle_webhook(
        db, provider, dict(request.headers), raw, body, background=background
    )
