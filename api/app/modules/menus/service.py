"""Regra de negócio do módulo `menus`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.modules.categories.models import Category
from app.modules.menus.models import Menu, MenuItem


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


async def _resolve_url(db: AsyncSession, item: MenuItem) -> str:
    if item.link_type == "category" and item.category_id:
        cat = await db.get(Category, item.category_id)
        if cat:
            return f"/categoria/{cat.path}"
    return item.url or "#"


async def get_location(db: AsyncSession, location: str, *, only_active: bool = True) -> list[dict]:
    menus = await db.scalars(
        select(Menu)
        .where(Menu.location == location)
        .options(selectinload(Menu.items))
        .order_by(Menu.position)
    )
    out: list[dict] = []
    for menu in menus:
        if only_active and not menu.is_active:
            continue
        items = [i for i in menu.items if not i.parent_id]
        by_parent: dict[uuid.UUID, list[MenuItem]] = {}
        for i in menu.items:
            if i.parent_id:
                by_parent.setdefault(i.parent_id, []).append(i)

        async def node(i: MenuItem) -> dict:
            children = sorted(by_parent.get(i.id, []), key=lambda x: x.position)
            size_shortcuts = []
            if i.show_size_shortcuts and i.size_shortcut_category_id:
                cat = await db.get(Category, i.size_shortcut_category_id)
                if cat:
                    from app.modules.products.service import _facets

                    facets = await _facets(db, None)
                    size_shortcuts = [
                        {"label": s["value"], "url": f"/categoria/{cat.path}?size={s['value']}"}
                        for s in facets.get("sizes", [])
                    ]
            return {
                "id": str(i.id),
                "label": i.label,
                "url": await _resolve_url(db, i),
                "highlight": i.highlight,
                "is_megamenu": i.is_megamenu,
                "size_shortcuts": size_shortcuts,
                "children": [await node(c) for c in children],
            }

        out.append(
            {
                "id": str(menu.id),
                "location": menu.location,
                "name": menu.name,
                "items": [await node(i) for i in sorted(items, key=lambda x: x.position)],
            }
        )
    return out


async def list_menus(db: AsyncSession) -> list[Menu]:
    return list(await db.scalars(select(Menu).options(selectinload(Menu.items)).order_by(Menu.position)))


async def list_items(db: AsyncSession, menu_id: str) -> list[MenuItem]:
    menu = await db.get(Menu, _uuid(menu_id))
    if not menu:
        raise NotFoundError("Menu não encontrado.")
    rows = await db.scalars(
        select(MenuItem).where(MenuItem.menu_id == menu.id).order_by(MenuItem.position)
    )
    return list(rows)


async def create_menu(db: AsyncSession, data: dict) -> Menu:
    menu = Menu(**data)
    db.add(menu)
    await db.flush()
    return menu


async def update_menu(db: AsyncSession, menu_id: str, data: dict) -> Menu:
    menu = await db.get(Menu, _uuid(menu_id))
    if not menu:
        raise NotFoundError("Menu não encontrado.")
    for k, v in data.items():
        if v is not None:
            setattr(menu, k, v)
    return menu


async def add_item(db: AsyncSession, menu_id: str, data: dict) -> MenuItem:
    menu = await db.get(Menu, _uuid(menu_id))
    if not menu:
        raise NotFoundError("Menu não encontrado.")
    item = MenuItem(menu_id=menu.id, **_clean_item(data))
    db.add(item)
    await db.flush()
    return item


async def update_item(db: AsyncSession, item_id: str, data: dict) -> MenuItem:
    item = await db.get(MenuItem, _uuid(item_id))
    if not item:
        raise NotFoundError("Item não encontrado.")
    for k, v in _clean_item(data, partial=True).items():
        setattr(item, k, v)
    return item


async def delete_item(db: AsyncSession, item_id: str) -> None:
    item = await db.get(MenuItem, _uuid(item_id))
    if item:
        await db.delete(item)


async def reorder_items(db: AsyncSession, items: list[dict]) -> None:
    for it in items:
        row = await db.get(MenuItem, _uuid(it["id"]))
        if row:
            row.position = it.get("position", row.position)
            if "parent_id" in it:
                row.parent_id = _uuid(it["parent_id"]) if it["parent_id"] else None


def _clean_item(data: dict, *, partial: bool = False) -> dict:
    fields = {
        "parent_id", "label", "link_type", "category_id", "url", "position",
        "is_megamenu", "highlight", "show_size_shortcuts", "size_shortcut_category_id",
    }
    out = {}
    for k, v in data.items():
        if k not in fields:
            continue
        if partial and v is None:
            continue
        if k in ("parent_id", "category_id", "size_shortcut_category_id") and v:
            v = _uuid(v)
        out[k] = v
    return out
