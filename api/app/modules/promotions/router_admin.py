"""Rotas administrativas do módulo `promotions`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.promotions import service
from app.modules.promotions.schemas import CouponCreateIn, CouponOut, CouponUpdateIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


def _out(c) -> dict:
    return {
        "id": str(c.id),
        "code": c.code,
        "description": c.description,
        "type": c.type,
        "value": float(c.value),
        "min_order_cents": c.min_order_cents,
        "max_discount_cents": c.max_discount_cents,
        "starts_at": c.starts_at,
        "ends_at": c.ends_at,
        "usage_limit": c.usage_limit,
        "usage_limit_per_user": c.usage_limit_per_user,
        "is_active": c.is_active,
        "used_count": c.used_count,
    }


@router.get("", response_model=list[CouponOut])
async def list_coupons(db: DbDep, _: AdminDep):
    return [_out(c) for c in await service.list_coupons(db)]


@router.post("", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
async def create_coupon(body: CouponCreateIn, db: DbDep, _: EditorDep):
    return _out(await service.create_coupon(db, body.model_dump()))


@router.patch("/{coupon_id}", response_model=CouponOut)
async def update_coupon(coupon_id: str, body: CouponUpdateIn, db: DbDep, _: EditorDep):
    return _out(await service.update_coupon(db, coupon_id, body.model_dump(exclude_unset=True)))


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(coupon_id: str, db: DbDep, _: EditorDep):
    await service.delete_coupon(db, coupon_id)
