"""Rotas administrativas do módulo `menus`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.menus import service

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_menus(db: DbDep, _: AdminDep) -> list[dict]:
    menus = await service.list_menus(db)
    return [
        {
            "id": str(m.id),
            "location": m.location,
            "name": m.name,
            "position": m.position,
            "is_active": m.is_active,
            "items": [
                {
                    "id": str(i.id),
                    "parent_id": str(i.parent_id) if i.parent_id else None,
                    "label": i.label,
                    "link_type": i.link_type,
                    "category_id": str(i.category_id) if i.category_id else None,
                    "url": i.url,
                    "position": i.position,
                    "is_megamenu": i.is_megamenu,
                    "highlight": i.highlight,
                    "show_size_shortcuts": i.show_size_shortcuts,
                }
                for i in sorted(m.items, key=lambda x: x.position)
            ],
        }
        for m in menus
    ]


@router.get("/{location}/resolved")
async def resolved(location: str, db: DbDep, _: AdminDep) -> list[dict]:
    return await service.get_location(db, location, only_active=False)


@router.get("/{menu_id}/items")
async def list_items(menu_id: str, db: DbDep, _: AdminDep) -> list[dict]:
    items = await service.list_items(db, menu_id)
    return [
        {
            "id": str(i.id),
            "menu_id": str(i.menu_id),
            "parent_id": str(i.parent_id) if i.parent_id else None,
            "label": i.label,
            "link_type": i.link_type,
            "category_id": str(i.category_id) if i.category_id else None,
            "url": i.url,
            "position": i.position,
            "is_megamenu": i.is_megamenu,
            "highlight": i.highlight,
            "show_size_shortcuts": i.show_size_shortcuts,
            "size_shortcut_category_id": (
                str(i.size_shortcut_category_id) if i.size_shortcut_category_id else None
            ),
        }
        for i in items
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_menu(payload: dict, db: DbDep, _: EditorDep) -> dict:
    m = await service.create_menu(db, {k: payload[k] for k in ("location", "name", "position", "is_active") if k in payload})
    return {"id": str(m.id)}


@router.patch("/{menu_id}")
async def update_menu(menu_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    m = await service.update_menu(db, menu_id, payload)
    return {"id": str(m.id)}


@router.post("/{menu_id}/items", status_code=status.HTTP_201_CREATED)
async def add_item(menu_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    i = await service.add_item(db, menu_id, payload)
    return {"id": str(i.id)}


@router.patch("/items/{item_id}")
async def update_item(item_id: str, payload: dict, db: DbDep, _: EditorDep) -> dict:
    i = await service.update_item(db, item_id, payload)
    return {"id": str(i.id)}


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete_item(db, item_id)


@router.post("/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder(payload: dict, db: DbDep, _: EditorDep) -> None:
    await service.reorder_items(db, payload.get("items", []))
