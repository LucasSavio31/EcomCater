"""Rotas administrativas do módulo `theme` — aparência + páginas."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.theme import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def get_theme(db: DbDep, _: AdminDep) -> dict:
    return service.theme_out(await service.get_theme(db))


@router.put("")
async def update_theme(payload: dict, db: DbDep, _: EditorDep) -> dict:
    return service.theme_out(await service.update_theme(db, payload))


@router.post("/image/{kind}")
async def upload_theme_image(
    kind: str, db: DbDep, _: EditorDep, file: Annotated[UploadFile, File()]
) -> dict:
    raw = await file.read()
    row = await service.set_theme_image(db, kind, raw, file.filename or f"{kind}.png")
    return service.theme_out(row)


@router.get("/pages")
async def list_pages(db: DbDep, _: AdminDep) -> list[dict]:
    return [service.page_out(p) for p in await service.list_pages(db)]


@router.post("/pages", status_code=status.HTTP_201_CREATED)
async def create_page(payload: dict, db: DbDep, _: EditorDep) -> dict:
    return service.page_out(await service.create_page(db, payload))


@router.patch("/pages/{page_id}")
async def update_page(page_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    return service.page_out(await service.update_page(db, page_id, payload))


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(page_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete_page(db, page_id)
