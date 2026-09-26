"""Rota pública do módulo `analytics` — config das tags para a loja (sem segredos)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics import service
from app.modules.analytics.schemas import AnalyticsPublicConfig
from app.modules.domains import sites

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/config", response_model=AnalyticsPublicConfig)
async def public_config(db: DbDep, site: str | None = None):
    """Tags do domínio `site` (a loja manda o próprio host) -- multi-domínio:
    cada domínio só carrega os próprios pixels. Sem `site`/desconhecido =
    domínio principal."""
    await sites.refresh()
    row = await service.get_for_site(db, site)
    return service.to_public(row)
