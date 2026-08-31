"""Rotas administrativas do módulo `size_charts`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.size_charts import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_charts(db: DbDep, _: AdminDep) -> list[dict]:
    return await service.list_all(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chart(payload: dict, db: DbDep, _: EditorDep) -> dict:
    return service.out(await service.create(db, payload))


@router.patch("/{chart_id}")
async def update_chart(chart_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    return service.out(await service.update(db, chart_id, payload))


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(chart_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete(db, chart_id)
