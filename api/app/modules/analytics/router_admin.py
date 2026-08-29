"""Rotas administrativas do módulo `analytics`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.analytics import service
from app.modules.analytics.schemas import AnalyticsAdminConfig, AnalyticsUpdateIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin"))]


@router.get("", response_model=AnalyticsAdminConfig)
async def get_config(db: DbDep, _: AdminDep):
    return service.to_admin(await service.get_settings(db))


@router.put("", response_model=AnalyticsAdminConfig)
async def update_config(payload: AnalyticsUpdateIn, db: DbDep, _: EditorDep):
    row = await service.update_settings(db, payload.model_dump(exclude_unset=True))
    return service.to_admin(row)
