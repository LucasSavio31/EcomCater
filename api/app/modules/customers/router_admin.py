"""Rotas administrativas de clientes: CRUD de dados pessoais + endereços.

Ao editar dados do cliente ou o endereço padrão, os pedidos ATIVOS
(pending_payment / paid / processing) são atualizados também. Pedidos já
enviados/entregues/cancelados ficam como estão (snapshot histórico).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.core.errors import NotFoundError, ValidationError
from app.modules.admin.models import AdminUser
from app.modules.customers.models import CustomerAddress, User
from app.modules.orders.models import Order
from app.shared.cpf import is_valid_cpf, only_digits

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]

_ACTIVE_STATUSES = ("pending_payment", "paid", "processing")
_ADDR_FIELDS = (
    "label", "recipient_name", "zip", "street", "number", "complement",
    "district", "city", "state", "country", "is_default",
)


def _addr_out(a: CustomerAddress) -> dict:
    return {
        "id": str(a.id),
        "label": a.label,
        "recipient_name": a.recipient_name,
        "zip": a.zip,
        "street": a.street,
        "number": a.number,
        "complement": a.complement,
        "district": a.district,
        "city": a.city,
        "state": a.state,
        "country": a.country,
        "is_default": a.is_default,
    }


def _user_out(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "phone": u.phone,
        "cpf": u.cpf,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def _propagate(db: AsyncSession, user: User, address: CustomerAddress | None) -> int:
    """Aplica os dados do cliente aos pedidos ativos. Retorna quantos foram tocados."""
    from app.modules.orders.service import record_event

    orders = list(
        await db.scalars(
            select(Order)
            .where(Order.user_id == user.id, Order.status.in_(_ACTIVE_STATUSES))
            .options(selectinload(Order.items))
        )
    )
    for o in orders:
        o.email = user.email
        o.cpf = user.cpf
        addr = dict(o.shipping_address_json or {})
        addr["recipient_name"] = user.full_name
        if user.phone:
            addr["phone"] = user.phone
        if address is not None:
            for f in ("zip", "street", "number", "complement", "district", "city", "state", "country"):
                addr[f] = getattr(address, f)
        o.shipping_address_json = addr
        await record_event(
            db, o, type="edited", actor_type="admin",
            message="Dados do cliente atualizados no cadastro",
        )
    return len(orders)


@router.get("")
async def list_customers(
    db: DbDep,
    _: AdminDep,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(User.email.ilike(like), User.full_name.ilike(like), User.cpf.ilike(like))
        )
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    users = list(
        await db.scalars(
            stmt.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    )
    ids = [u.id for u in users]
    stats: dict[str, tuple[int, int]] = {}
    if ids:
        rows = await db.execute(
            select(
                Order.user_id,
                func.count(Order.id),
                func.coalesce(func.sum(Order.grand_total_cents), 0),
            )
            .where(Order.user_id.in_(ids))
            .group_by(Order.user_id)
        )
        for uid, n, total_cents in rows:
            stats[str(uid)] = (int(n), int(total_cents))
    items = []
    for u in users:
        n, spent = stats.get(str(u.id), (0, 0))
        items.append({**_user_out(u), "orders_count": n, "total_spent_cents": spent})
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{cid}")
async def get_customer(cid: str, db: DbDep, _: AdminDep) -> dict:
    user = await db.scalar(
        select(User).where(User.id == cid).options(selectinload(User.addresses))
    )
    if not user:
        raise NotFoundError("Cliente não encontrado.")
    orders = list(
        await db.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(20)
        )
    )
    return {
        **_user_out(user),
        "addresses": [_addr_out(a) for a in sorted(user.addresses, key=lambda x: not x.is_default)],
        "orders": [
            {
                "number": o.number,
                "status": o.status,
                "payment_status": o.payment_status,
                "grand_total_cents": o.grand_total_cents,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "active": o.status in _ACTIVE_STATUSES,
            }
            for o in orders
        ],
    }


class CustomerPatchIn(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    cpf: str | None = None
    is_active: bool | None = None


@router.patch("/{cid}")
async def update_customer(cid: str, body: CustomerPatchIn, db: DbDep, _: EditorDep) -> dict:
    user = await db.scalar(
        select(User).where(User.id == cid).options(selectinload(User.addresses))
    )
    if not user:
        raise NotFoundError("Cliente não encontrado.")
    data = body.model_dump(exclude_unset=True)
    if data.get("email"):
        dup = await db.scalar(
            select(User).where(User.email == data["email"], User.id != user.id)
        )
        if dup:
            raise ValidationError("Já existe outro cliente com esse e-mail.")
        user.email = data["email"].strip()
    if data.get("full_name"):
        user.full_name = data["full_name"].strip()
    if "phone" in data:
        user.phone = (data["phone"] or "").strip() or None
    if "cpf" in data:
        digits = only_digits(data["cpf"] or "")
        if digits and not is_valid_cpf(digits):
            raise ValidationError("CPF inválido.")
        user.cpf = digits or None
    if data.get("is_active") is not None:
        user.is_active = bool(data["is_active"])
    await db.flush()

    default_addr = next((a for a in user.addresses if a.is_default), None)
    touched = await _propagate(db, user, default_addr)
    return {**_user_out(user), "orders_updated": touched}


class AddressIn(BaseModel):
    label: str = "Endereço"
    recipient_name: str
    zip: str
    street: str
    number: str
    complement: str | None = None
    district: str
    city: str
    state: str
    country: str = "BR"
    is_default: bool = False


async def _get_user(db: AsyncSession, cid: str) -> User:
    user = await db.scalar(
        select(User).where(User.id == cid).options(selectinload(User.addresses))
    )
    if not user:
        raise NotFoundError("Cliente não encontrado.")
    return user


def _clean_addr_data(data: dict) -> dict:
    out = {k: v for k, v in data.items() if k in _ADDR_FIELDS}
    if "zip" in out:
        out["zip"] = only_digits(str(out["zip"]))[:8]
    if "state" in out:
        out["state"] = str(out["state"]).upper()[:2]
    return out


@router.post("/{cid}/addresses", status_code=201)
async def add_address(cid: str, body: AddressIn, db: DbDep, _: EditorDep) -> dict:
    user = await _get_user(db, cid)
    data = _clean_addr_data(body.model_dump())
    if data.get("is_default"):
        for a in user.addresses:
            a.is_default = False
    addr = CustomerAddress(user_id=user.id, **data)
    db.add(addr)
    await db.flush()
    if addr.is_default:
        await _propagate(db, user, addr)
    return _addr_out(addr)


@router.patch("/{cid}/addresses/{aid}")
async def update_address(cid: str, aid: str, body: AddressIn, db: DbDep, _: EditorDep) -> dict:
    user = await _get_user(db, cid)
    addr = next((a for a in user.addresses if str(a.id) == aid), None)
    if not addr:
        raise NotFoundError("Endereço não encontrado.")
    data = _clean_addr_data(body.model_dump())
    if data.get("is_default"):
        for a in user.addresses:
            a.is_default = False
    for k, v in data.items():
        setattr(addr, k, v)
    await db.flush()
    if addr.is_default:
        await _propagate(db, user, addr)
    return _addr_out(addr)


@router.delete("/{cid}/addresses/{aid}", status_code=204)
async def delete_address(cid: str, aid: str, db: DbDep, _: EditorDep) -> None:
    user = await _get_user(db, cid)
    addr = next((a for a in user.addresses if str(a.id) == aid), None)
    if addr:
        await db.delete(addr)
