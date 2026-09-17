"""Rotas administrativas do módulo `notifications`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.modules.admin.models import AdminUser
from app.modules.notifications import service
from app.modules.notifications.models import Notification

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]


def _out(row: Notification) -> dict:
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "message": row.message,
        "link_path": row.link_path,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "created_at": row.created_at.isoformat(),
    }


@admin_router.get("")
async def list_notifications(db: DbDep, _: AdminDep, limit: int = Query(default=50, le=200)) -> dict:
    rows = await service.list_recent(db, limit=limit)
    return {"items": [_out(r) for r in rows], "unread_count": await service.unread_count(db)}


@admin_router.post("/{notification_id}/read")
async def mark_read(notification_id: str, db: DbDep, _: AdminDep) -> dict:
    row = await service.mark_read(db, notification_id)
    await db.commit()
    return _out(row)


@admin_router.post("/read-all")
async def mark_all_read(db: DbDep, _: AdminDep) -> dict:
    await service.mark_all_read(db)
    await db.commit()
    return {"ok": True}


@admin_router.delete("/{notification_id}")
async def delete_one(notification_id: str, db: DbDep, _: AdminDep) -> dict:
    await service.delete_one(db, notification_id)
    await db.commit()
    return {"ok": True}


@admin_router.delete("")
async def delete_all(db: DbDep, _: AdminDep) -> dict:
    await service.delete_all(db)
    await db.commit()
    return {"ok": True}
