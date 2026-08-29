"""Rotas públicas do módulo `cart`.

O carrinho é identificado por cookie `cart_token` (convidado) ou pelo cliente
logado. Toda resposta re-emite o cookie.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer_optional
from app.modules.cart import service
from app.modules.cart.schemas import (
    AddItemIn,
    ApplyCouponIn,
    CartOut,
    SelectShippingIn,
    SetZipIn,
    UpdateItemIn,
)
from app.modules.customers.models import User

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
UserDep = Annotated[User | None, Depends(get_current_customer_optional)]
COOKIE = "cart_token"
COOKIE_MAX_AGE = service.CART_TTL_DAYS * 86400


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        COOKIE, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", path="/"
    )


async def _resolve(db, token, user):
    return await service.get_or_create(db, token=token, user_id=str(user.id) if user else None)


@router.get("", response_model=CartOut)
async def get_cart(
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    body: AddItemIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.add_item(db, cart, body.variant_id, body.quantity)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(
    item_id: str,
    body: UpdateItemIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.update_item(db, cart, item_id, body.quantity)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.delete("/items/{item_id}", response_model=CartOut)
async def remove_item(
    item_id: str,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.remove_item(db, cart, item_id)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.put("/zip", response_model=CartOut)
async def set_zip(
    body: SetZipIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.set_zip(db, cart, body.zip)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.post("/coupon", response_model=CartOut)
async def apply_coupon(
    body: ApplyCouponIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart, err = await service.apply_coupon(db, cart, body.code)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart, coupon_error=err)


@router.delete("/coupon", response_model=CartOut)
async def remove_coupon(
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.remove_coupon(db, cart)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)


@router.get("/shipping-options")
async def shipping_options(
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    from app.modules.shipping import service as shipping

    cart = await _resolve(db, cart_token, user)
    return await shipping.quote_for_cart(db, cart)


@router.post("/shipping", response_model=CartOut)
async def select_shipping(
    body: SelectShippingIn,
    response: Response,
    db: DbDep,
    user: UserDep,
    cart_token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
):
    cart = await _resolve(db, cart_token, user)
    cart = await service.select_shipping(db, cart, body.service_id)
    _set_cookie(response, cart.session_token)
    return await service.serialize(db, cart)
