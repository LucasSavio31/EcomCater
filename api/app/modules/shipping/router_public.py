"""Rotas públicas do módulo `shipping`."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import DomainError
from app.core.ratelimit import rate_limit
from app.modules.shipping import service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.schemas import QuoteIn

logger = logging.getLogger("shipping.oauth")

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/quote")
async def quote(
    body: QuoteIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("30/minute", scope="ship-quote"))],
) -> list[dict]:
    packages = [
        Package(
            weight_grams=i.weight_grams,
            length_mm=i.length_mm,
            width_mm=i.width_mm,
            height_mm=i.height_mm,
            insurance_cents=i.price_cents,
            quantity=i.quantity,
        )
        for i in (body.items or [])
    ] or [Package(weight_grams=300, length_mm=200, width_mm=150, height_mm=100)]
    return await service.quote(db, dest_zip=body.dest_zip, packages=packages)


@router.get("/melhor-envio/callback")
async def melhor_envio_callback(
    db: DbDep,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
) -> RedirectResponse:
    """Callback do OAuth do Melhor Envio: troca o code por token e volta ao admin."""
    admin = f"{settings.admin_url.rstrip('/')}/frete"
    if error or not code:
        return RedirectResponse(f"{admin}?me=error", status_code=303)
    try:
        await service.melhor_envio_exchange_code(db, code=code, state=state)
    except DomainError as exc:
        logger.warning("Callback Melhor Envio falhou: %s", exc)
        return RedirectResponse(f"{admin}?me=error", status_code=303)
    return RedirectResponse(f"{admin}?me=connected", status_code=303)
