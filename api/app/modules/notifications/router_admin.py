"""Rotas administrativas do módulo `notifications`."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_admin
from app.core.security import decode_token
from app.modules.admin.models import AdminUser
from app.modules.notifications import service, stream
from app.modules.theme.service import get_theme

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]

_out = service.notification_out


async def _admin_id_from_ws_token(token: str | None) -> uuid.UUID | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001
        return None
    if payload.get("type") != "access" or payload.get("scope") != "admin":
        return None
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None


@admin_router.get("")
async def list_notifications(db: DbDep, _: AdminDep, limit: int = Query(default=50, le=200)) -> dict:
    rows = await service.list_recent(db, limit=limit)
    theme = await get_theme(db)
    return {
        "items": [_out(r) for r in rows],
        "unread_count": await service.unread_count(db),
        "sound_sale_enabled": theme.sound_sale_enabled,
        "sound_return_enabled": theme.sound_return_enabled,
    }


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


@admin_router.websocket("/stream")
async def notifications_stream(websocket: WebSocket) -> None:
    """Push em tempo real pro sininho -- o browser não manda header em
    WebSocket, então o access token vem por `?token=` (mesmo padrão de
    `get_current_admin_downloadable`)."""
    admin_id = await _admin_id_from_ws_token(websocket.query_params.get("token"))
    if admin_id is None:
        await websocket.close(code=4401)
        return
    async with SessionLocal() as db:
        admin = await db.get(AdminUser, admin_id)
    if not admin or not admin.is_active:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = stream.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        stream.unsubscribe(queue)
