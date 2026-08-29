"""Rotas públicas do módulo `orders` — checkout e acompanhamento."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer_optional
from app.core.ratelimit import rate_limit
from app.modules.cart import service as cart_service
from app.modules.orders import service
from app.modules.orders.schemas import CheckoutIn, OrderOut
from app.modules.customers.models import User

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[User | None, Depends(get_current_customer_optional)]


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def checkout(
    body: CheckoutIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    _rl: Annotated[None, Depends(rate_limit("20/minute", scope="checkout"))],
    cart_token: Annotated[str | None, Cookie(alias="cart_token")] = None,
):
    cart = await cart_service.get_or_create(
        db, token=cart_token, user_id=str(user.id) if user else None
    )
    if body.shipping_service_id and cart.shipping_zip:
        cart = await cart_service.select_shipping(db, cart, body.shipping_service_id)

    order = await service.create_from_cart(
        db,
        cart,
        email=body.email,
        cpf=body.cpf,
        shipping_address=body.shipping_address.model_dump(),
        billing_address=body.billing_address.model_dump() if body.billing_address else None,
        customer_note=body.customer_note,
        idempotency_key=body.idempotency_key,
    )
    await cart_service.clear(db, cart)
    full = await service._load(db, order.id)
    return service.to_out(full)


@router.get("")
async def my_orders(db: DbDep, user: UserDep):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.modules.orders.models import Order

    if not user:
        from app.core.errors import AuthError

        raise AuthError("Faça login para ver seus pedidos.")
    rows = await db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.items), selectinload(Order.events))
        .order_by(Order.placed_at.desc().nullslast())
    )
    return [service.to_out(o) for o in rows]


@router.get("/{number}", response_model=OrderOut)
async def get_order(
    number: str,
    db: DbDep,
    user: UserDep,
    email: str | None = Query(None),
):
    if user:
        order = await service.get_by_number(db, number)
        if order.user_id and str(order.user_id) == str(user.id):
            return service.to_out(order)
    order = await service.get_by_number(db, number, email=email)
    return service.to_out(order)
