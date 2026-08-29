"""Rotas públicas do módulo `shipping`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.modules.shipping import service
from app.modules.shipping.providers.base import Package
from app.modules.shipping.schemas import QuoteIn

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
