"""Rotas públicas do módulo `customers`: auth de cliente, perfil e endereços."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_customer
from app.core.ratelimit import rate_limit
from app.modules.customers import service
from app.modules.customers.models import User
from app.modules.customers.schemas import (
    AddressIn,
    AddressOut,
    CustomerOut,
    CustomerUpdateIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentCustomer = Annotated[User, Depends(get_current_customer)]


def _out(user: User) -> CustomerOut:
    return CustomerOut.model_validate({**user.__dict__, "id": str(user.id)})


@router.post("/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("20/minute", scope="register"))],
):
    _, pair = await service.register(
        db, full_name=body.full_name, email=body.email,
        password=body.password, phone=body.phone,
    )
    return TokenOut(**pair)


@router.post("/auth/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    db: DbDep,
    _rl: Annotated[None, Depends(rate_limit("15/minute", scope="login"))],
):
    _, pair = await service.login(db, body.email, body.password)
    return TokenOut(**pair)


@router.post("/auth/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: DbDep):
    return TokenOut(**await service.refresh(db, body.refresh_token))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshIn, db: DbDep):
    await service.logout(db, body.refresh_token)


@router.get("/me", response_model=CustomerOut)
async def me(customer: CurrentCustomer):
    return _out(customer)


@router.patch("/me", response_model=CustomerOut)
async def update_me(body: CustomerUpdateIn, db: DbDep, customer: CurrentCustomer):
    user = await service.update_profile(db, customer, body.model_dump(exclude_unset=True))
    return _out(user)


@router.get("/me/addresses", response_model=list[AddressOut])
async def list_addresses(db: DbDep, customer: CurrentCustomer):
    rows = await service.list_addresses(db, customer)
    return [AddressOut.model_validate({**r.__dict__, "id": str(r.id)}) for r in rows]


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_address(body: AddressIn, db: DbDep, customer: CurrentCustomer):
    addr = await service.create_address(db, customer, body.model_dump())
    return AddressOut.model_validate({**addr.__dict__, "id": str(addr.id)})


@router.patch("/me/addresses/{address_id}", response_model=AddressOut)
async def update_address(address_id: str, body: AddressIn, db: DbDep, customer: CurrentCustomer):
    addr = await service.update_address(db, customer, address_id, body.model_dump())
    return AddressOut.model_validate({**addr.__dict__, "id": str(addr.id)})


@router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(address_id: str, db: DbDep, customer: CurrentCustomer):
    await service.delete_address(db, customer, address_id)


# --------------------------------------------------------------- wishlist
@router.get("/me/wishlist")
async def get_wishlist(db: DbDep, customer: CurrentCustomer) -> list[dict]:
    return await service.list_wishlist(db, customer)


@router.post("/me/wishlist/{product_id}", status_code=status.HTTP_201_CREATED)
async def add_wishlist(product_id: str, db: DbDep, customer: CurrentCustomer) -> dict:
    await service.add_to_wishlist(db, customer, product_id)
    return {"ok": True}


@router.delete("/me/wishlist/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wishlist(product_id: str, db: DbDep, customer: CurrentCustomer) -> None:
    await service.remove_from_wishlist(db, customer, product_id)
