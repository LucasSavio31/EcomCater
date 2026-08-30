"""Registro do módulo `banners` (toggleable)."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.module_registry import ModuleSpec, register
from app.modules.admin.models import AdminUser
from app.modules.banners import service

public_router = APIRouter()
admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@public_router.get("")
async def list_banners(db: DbDep, slot: str | None = None) -> list[dict]:
    return await service.list_public(db, slot)


@admin_router.get("")
async def admin_list(db: DbDep, _: Annotated[AdminUser, Depends(get_current_admin)]) -> list[dict]:
    return await service.list_admin(db)


@admin_router.post("", status_code=status.HTTP_201_CREATED)
async def create_banner(payload: dict, db: DbDep, _: EditorDep) -> dict:
    b = await service.create(db, payload)
    return {"id": str(b.id)}


@admin_router.patch("/{banner_id}")
async def update_banner(banner_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    b = await service.update(db, banner_id, payload)
    return {"id": str(b.id)}


@admin_router.delete("/{banner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_banner(banner_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete(db, banner_id)


@admin_router.post("/{banner_id}/image")
async def upload_image(
    banner_id: str,
    db: DbDep,
    _: EditorDep,
    file: Annotated[UploadFile, File()],
    variant: Annotated[str, Form()] = "desktop",
) -> dict:
    raw = await file.read()
    b = await service.set_image(
        db, banner_id, raw, file.filename or "banner.png",
        variant="mobile" if variant == "mobile" else "desktop",
    )
    return {"id": str(b.id)}


@admin_router.delete("/{banner_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def clear_image(
    banner_id: str,
    db: DbDep,
    _: EditorDep,
    variant: str = Query("desktop"),
) -> None:
    await service.clear_image(db, banner_id, "mobile" if variant == "mobile" else "desktop")


spec = register(
    ModuleSpec(
        slug="banners",
        label="Banners",
        kind="feature",
        toggleable=True,
        default_enabled=True,
        public_router=public_router,
        admin_router=admin_router,
        tags=["banners"],
    )
)
