"""Rota pública do módulo `analytics` — config das tags para a loja (sem segredos)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics import service
from app.modules.analytics.schemas import AnalyticsPublicConfig

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/config", response_model=AnalyticsPublicConfig)
async def public_config(db: DbDep):
    row = await service.get_settings(db)
    return service.to_public(row)
