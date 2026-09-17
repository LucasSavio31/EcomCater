"""Rotas administrativas do módulo `upseller`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.modules.admin.models import AdminUser
from app.modules.upseller import service

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin"))]


class CredentialsIn(BaseModel):
    client_id: str | None = None
    api_token: str | None = None


class TogglesIn(BaseModel):
    stock_sync_enabled: bool | None = None


def _status_out(cfg) -> dict:
    return {
        "has_client_id": bool(cfg.client_id),
        "has_api_token": bool(cfg.api_token),
        "connected": service.is_connected(cfg),
        "stock_sync_enabled": cfg.stock_sync_enabled,
        "last_sync_at": cfg.last_sync_at or None,
        "last_sync_summary": cfg.last_sync_summary or None,
    }


@admin_router.get("")
async def get_state(db: DbDep, _: EditorDep) -> dict:
    cfg = await service.load_config(db)
    return _status_out(cfg)


@admin_router.put("/credentials")
async def update_credentials(body: CredentialsIn, db: DbDep, _: EditorDep) -> dict:
    cfg = await service.save_config(db, body.model_dump(exclude_unset=True))
    return _status_out(cfg)


@admin_router.put("/toggles")
async def update_toggles(body: TogglesIn, db: DbDep, _: EditorDep) -> dict:
    cfg = await service.save_config(db, body.model_dump(exclude_unset=True))
    return _status_out(cfg)


@admin_router.post("/test")
async def test_connection(db: DbDep, _: EditorDep) -> dict:
    return await service.test_connection(db)


@admin_router.get("/warehouses")
async def warehouses(db: DbDep, _: EditorDep) -> list[dict]:
    return await service.list_warehouses(db)


@admin_router.post("/sync")
async def sync_now(db: DbDep, _: EditorDep) -> dict:
    return await service.sync_stock(db)
