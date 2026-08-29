"""Rotas administrativas do módulo `categories`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.categories import service
from app.modules.categories.schemas import (
    CategoryCreateIn,
    CategoryReorderIn,
    CategoryUpdateIn,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_categories(db: DbDep, _: AdminDep) -> list[dict]:
    return [service.to_out(c) for c in await service.list_all(db)]


@router.get("/tree")
async def admin_tree(db: DbDep, _: AdminDep) -> list[dict]:
    return await service.build_tree(db, only_active=False)


@router.get("/{category_id}")
async def get_category(category_id: str, db: DbDep, _: AdminDep) -> dict:
    return service.to_out(await service.get_by_id(db, category_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreateIn, db: DbDep, _: EditorDep) -> dict:
    cat = await service.create(db, body.model_dump())
    return service.to_out(cat)


@router.patch("/{category_id}")
async def update_category(
    category_id: str, body: CategoryUpdateIn, db: DbDep, _: EditorDep
) -> dict:
    cat = await service.update(db, category_id, body.model_dump(exclude_unset=True))
    return service.to_out(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete(db, category_id)


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder(body: CategoryReorderIn, db: DbDep, _: EditorDep) -> None:
    await service.reorder(db, [i.model_dump() for i in body.items])


@router.post("/{category_id}/image")
async def upload_image(
    category_id: str, db: DbDep, _: EditorDep, file: Annotated[UploadFile, File()]
) -> dict:
    raw = await file.read()
    cat = await service.set_image(db, category_id, raw, file.filename or "categoria.png")
    return service.to_out(cat)
