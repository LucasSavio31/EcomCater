"""Regra de negócio do módulo `promotions` — validação e cálculo de cupons."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.promotions.models import Coupon, CouponRedemption

VALID_TYPES = {"percent", "fixed", "free_shipping"}


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


async def get_by_code(db: AsyncSession, code: str) -> Coupon | None:
    return await db.scalar(select(Coupon).where(func.lower(Coupon.code) == code.strip().lower()))


async def validate_for_cart(db: AsyncSession, code: str, cart) -> Coupon:
    coupon = await get_by_code(db, code)
    if not coupon or not coupon.is_active:
        raise ValidationError("Cupom inválido.")
    now = datetime.now(UTC)
    if coupon.starts_at and coupon.starts_at > now:
        raise ValidationError("Este cupom ainda não está válido.")
    if coupon.ends_at and coupon.ends_at < now:
        raise ValidationError("Este cupom expirou.")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise ValidationError("Este cupom atingiu o limite de uso.")

    items_total = sum(i.unit_price_cents * i.quantity for i in cart.items)
    if not cart.items:
        raise ValidationError("Adicione itens ao carrinho antes de aplicar o cupom.")
    if coupon.min_order_cents and items_total < coupon.min_order_cents:
        falta = (coupon.min_order_cents - items_total) / 100
        raise ValidationError(f"Pedido mínimo não atingido (faltam R$ {falta:.2f}).")

    if coupon.usage_limit_per_user is not None and cart.user_id:
        used = await db.scalar(
            select(func.count(CouponRedemption.id)).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.user_id == cart.user_id,
            )
        )
        if int(used or 0) >= coupon.usage_limit_per_user:
            raise ValidationError("Você já usou este cupom o número máximo de vezes.")

    return coupon


async def compute_discount(db: AsyncSession, cart, items_total: int) -> tuple[int, bool]:
    """Retorna (desconto_em_centavos, frete_gratis)."""
    if not cart.coupon_id:
        return 0, False
    coupon = await db.get(Coupon, cart.coupon_id)
    if not coupon or not coupon.is_active:
        return 0, False

    if coupon.type == "free_shipping":
        return 0, True
    if coupon.type == "percent":
        disc = round(items_total * float(coupon.value) / 100)
    elif coupon.type == "fixed":
        disc = int(float(coupon.value))
    else:
        disc = 0
    if coupon.max_discount_cents:
        disc = min(disc, coupon.max_discount_cents)
    return max(0, min(disc, items_total)), False


async def register_redemption(
    db: AsyncSession, *, coupon_id: uuid.UUID, order_id: uuid.UUID, user_id: uuid.UUID | None, discount_cents: int
) -> None:
    db.add(
        CouponRedemption(
            coupon_id=coupon_id,
            order_id=order_id,
            user_id=user_id,
            discount_cents=discount_cents,
            created_at=datetime.now(UTC),
        )
    )
    coupon = await db.get(Coupon, coupon_id)
    if coupon:
        coupon.used_count += 1


# --------------------------------------------------------------------- admin CRUD
async def list_coupons(db: AsyncSession) -> list[Coupon]:
    return list(await db.scalars(select(Coupon).order_by(Coupon.created_at.desc())))


async def create_coupon(db: AsyncSession, data: dict) -> Coupon:
    if data["type"] not in VALID_TYPES:
        raise ValidationError(f"Tipo inválido: {data['type']}")
    if await get_by_code(db, data["code"]):
        raise ConflictError("Já existe um cupom com esse código.")
    coupon = Coupon(**data)
    db.add(coupon)
    await db.flush()
    return coupon


async def update_coupon(db: AsyncSession, coupon_id: str, data: dict) -> Coupon:
    coupon = await db.get(Coupon, _uuid(coupon_id))
    if not coupon:
        raise NotFoundError("Cupom não encontrado.")
    if data.get("type") and data["type"] not in VALID_TYPES:
        raise ValidationError(f"Tipo inválido: {data['type']}")
    for k, v in data.items():
        if v is not None:
            setattr(coupon, k, v)
    return coupon


async def delete_coupon(db: AsyncSession, coupon_id: str) -> None:
    coupon = await db.get(Coupon, _uuid(coupon_id))
    if not coupon:
        raise NotFoundError("Cupom não encontrado.")
    used = await db.scalar(
        select(CouponRedemption.id).where(CouponRedemption.coupon_id == coupon.id).limit(1)
    )
    if used:
        raise ConflictError("Cupom já utilizado — desative em vez de excluir.")
    await db.delete(coupon)
