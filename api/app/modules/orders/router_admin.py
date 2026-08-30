"""Rotas administrativas do módulo `orders`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.orders import service
from app.modules.orders.models import Order
from app.modules.orders.schemas import NoteIn, OrderOut, StatusChangeIn
from app.modules.payment.models import Payment

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_orders(
    db: DbDep,
    _: AdminDep,
    status: str | None = None,
    payment_status: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict:
    return await service.admin_list(
        db,
        status=status,
        payment_status=payment_status,
        q=q,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("/bulk")
async def orders_bulk(db: DbDep, _: AdminDep, numbers: list[str] = Body(..., embed=True)) -> list[dict]:
    """Pedidos completos por número — usado pelas telas de PDF / etiquetas."""
    return await service.admin_bulk(db, numbers)


async def _payment_out(db: AsyncSession, order: Order) -> dict | None:
    p = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc())
    )
    if not p:
        return None
    return {
        "provider": p.provider,
        "method": p.method,
        "status": p.status,
        "amount_cents": p.amount_cents,
        "installments": p.installments,
        "provider_charge_id": p.provider_charge_id,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "boleto_url": p.boleto_url,
        "pix_qr_code": p.pix_qr_code,
    }


@router.get("/{number}/pulse")
async def order_pulse(number: str, db: DbDep, _: AdminDep) -> dict:
    return await service.order_pulse(db, number)


@router.get("/{number}")
async def get_order(number: str, db: DbDep, _: AdminDep) -> dict:
    order = await service.get_by_number(db, number)
    out = {**service.to_out(order), "payment": await _payment_out(db, order)}
    return await service.attach_variation_options(db, out)


@router.patch("/{number}")
async def edit_order(number: str, body: dict, db: DbDep, _: EditorDep) -> dict:
    order = await service.edit_order(db, number, body)
    out = {**service.to_out(order), "payment": await _payment_out(db, order)}
    return await service.attach_variation_options(db, out)


@router.delete("/{number}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_order(number: str, db: DbDep, _: EditorDep) -> None:
    await service.delete_order(db, number)


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
