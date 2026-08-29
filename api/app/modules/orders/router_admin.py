"""Rotas administrativas do módulo `orders`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.orders import service
from app.modules.orders.schemas import NoteIn, OrderOut, StatusChangeIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_orders(
    db: DbDep,
    _: AdminDep,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    return await service.admin_list(db, status=status, q=q, page=page, page_size=page_size)


@router.get("/{number}", response_model=OrderOut)
async def get_order(number: str, db: DbDep, _: AdminDep) -> dict:
    return service.to_out(await service.get_by_number(db, number))


@router.post("/{number}/status", response_model=OrderOut)
async def change_status(
    number: str, body: StatusChangeIn, db: DbDep, admin: EditorDep
) -> dict:
    order = await service.get_by_number(db, number)
    order = await service.transition(
        db, order, body.status, actor_type="admin", actor_id=str(admin.id), message=body.message
    )
    return service.to_out(await service._load(db, order.id))


@router.post("/{number}/notes", response_model=OrderOut)
async def add_note(number: str, body: NoteIn, db: DbDep, admin: EditorDep) -> dict:
    order = await service.get_by_number(db, number)
    await service.add_note(db, order, body.message, str(admin.id))
    return service.to_out(await service._load(db, order.id))
