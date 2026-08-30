"""Regra de negócio do módulo `customers`: auth de cliente + perfil + endereços."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError, NotFoundError, ValidationError
from app.core.events import emit
from app.core.security import decode_token, hash_password, issue_pair, verify_password
from app.modules.admin.models import AuthRefreshToken
from app.modules.customers.models import CustomerAddress, User


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _store_refresh(db: AsyncSession, user_id: str, pair: dict) -> None:
    db.add(
        AuthRefreshToken(
            subject_type="customer",
            subject_id=str(user_id),
            jti=pair["_refresh_jti"],
            token_hash=_hash_token(pair["refresh_token"]),
            expires_at=pair["_refresh_exp"],
            created_at=datetime.now(UTC),
        )
    )


async def register(
    db: AsyncSession,
    *,
    full_name: str,
    email: str,
    password: str,
    phone: str | None,
    cpf: str | None = None,
) -> tuple[User, dict]:
    if await db.scalar(select(User).where(User.email == email)):
        raise ConflictError("Já existe uma conta com esse e-mail.")
    from app.core.errors import ValidationError
    from app.shared.cpf import is_valid_cpf, only_digits

    cpf_digits = only_digits(cpf) if cpf else ""
    if cpf_digits and not is_valid_cpf(cpf_digits):
        raise ValidationError("CPF inválido.")
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        cpf=cpf_digits or None,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    pair = issue_pair(str(user.id), scope="customer")
    await _store_refresh(db, str(user.id), pair)
    await emit("customer.registered", {"user_id": str(user.id)})
    return user, pair


async def login(db: AsyncSession, email: str, password: str) -> tuple[User, dict]:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("E-mail ou senha inválidos.")
    pair = issue_pair(str(user.id), scope="customer")
    await _store_refresh(db, str(user.id), pair)
    await emit("customer.logged_in", {"user_id": str(user.id)})
    return user, pair


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("Refresh token inválido.") from exc
    if payload.get("type") != "refresh" or payload.get("scope") != "customer":
        raise AuthError("Refresh token inválido.")
    row = await db.scalar(select(AuthRefreshToken).where(AuthRefreshToken.jti == payload["jti"]))
    if not row or row.revoked_at is not None:
        raise AuthError("Sessão expirada.")
    row.revoked_at = datetime.now(UTC)
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise AuthError("Conta inativa.")
    pair = issue_pair(str(user.id), scope="customer")
    await _store_refresh(db, str(user.id), pair)
    return pair


async def logout(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except Exception:  # noqa: BLE001
        return
    row = await db.scalar(select(AuthRefreshToken).where(AuthRefreshToken.jti == payload.get("jti")))
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)


async def update_profile(db: AsyncSession, user: User, data: dict) -> User:
    if data.get("new_password"):
        if not data.get("current_password") or not verify_password(
            data["current_password"], user.password_hash
        ):
            raise AuthError("Senha atual incorreta.")
        user.password_hash = hash_password(data["new_password"])
    if data.get("cpf") is not None:
        from app.core.errors import ValidationError
        from app.shared.cpf import is_valid_cpf, only_digits

        digits = only_digits(data["cpf"])
        if digits and not is_valid_cpf(digits):
            raise ValidationError("CPF inválido.")
        data = {**data, "cpf": digits or None}
    for field in ("full_name", "phone", "cpf"):
        if data.get(field) is not None:
            setattr(user, field, data[field])
    return user


# --------------------------------------------------------------- endereços
async def list_addresses(db: AsyncSession, user: User) -> list[CustomerAddress]:
    return list(
        await db.scalars(
            select(CustomerAddress).where(CustomerAddress.user_id == user.id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
        )
    )


async def create_address(db: AsyncSession, user: User, data: dict) -> CustomerAddress:
    addr = CustomerAddress(user_id=user.id, **data)
    if data.get("is_default"):
        await _clear_default(db, user)
    db.add(addr)
    await db.flush()
    return addr


async def update_address(db: AsyncSession, user: User, address_id: str, data: dict) -> CustomerAddress:
    addr = await db.get(CustomerAddress, uuid.UUID(address_id))
    if not addr or addr.user_id != user.id:
        raise NotFoundError("Endereço não encontrado.")
    if data.get("is_default"):
        await _clear_default(db, user)
    for k, v in data.items():
        setattr(addr, k, v)
    return addr


async def delete_address(db: AsyncSession, user: User, address_id: str) -> None:
    addr = await db.get(CustomerAddress, uuid.UUID(address_id))
    if not addr or addr.user_id != user.id:
        raise NotFoundError("Endereço não encontrado.")
    await db.delete(addr)


async def _clear_default(db: AsyncSession, user: User) -> None:
    for a in await db.scalars(
        select(CustomerAddress).where(
            CustomerAddress.user_id == user.id, CustomerAddress.is_default.is_(True)
        )
    ):
        a.is_default = False


async def merge_guest_cart(db: AsyncSession, payload: dict) -> None:
    """Placeholder — implementado na Fase 4 (subscriber de `customer.logged_in`)."""
    _ = (db, payload)


# --------------------------------------------------------------- wishlist
async def _get_wishlist(db: AsyncSession, user: User):
    from app.modules.customers.models import Wishlist

    wl = await db.scalar(select(Wishlist).where(Wishlist.user_id == user.id))
    if not wl:
        wl = Wishlist(user_id=user.id)
        db.add(wl)
        await db.flush()
    return wl


async def list_wishlist(db: AsyncSession, user: User) -> list[dict]:
    from sqlalchemy.orm import selectinload

    from app.modules.customers.models import WishlistItem
    from app.modules.products.models import Product
    from app.modules.products.service import list_item

    wl = await _get_wishlist(db, user)
    rows = await db.scalars(
        select(Product)
        .join(WishlistItem, WishlistItem.product_id == Product.id)
        .where(WishlistItem.wishlist_id == wl.id)
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    return [list_item(p) for p in rows]


async def add_to_wishlist(db: AsyncSession, user: User, product_id: str) -> None:
    from app.modules.customers.models import WishlistItem
    from app.modules.products.models import Product

    wl = await _get_wishlist(db, user)
    pid = uuid.UUID(product_id)
    if not await db.get(Product, pid):
        raise NotFoundError("Produto não encontrado.")
    exists = await db.scalar(
        select(WishlistItem).where(
            WishlistItem.wishlist_id == wl.id, WishlistItem.product_id == pid
        )
    )
    if not exists:
        from datetime import UTC, datetime

        db.add(WishlistItem(wishlist_id=wl.id, product_id=pid, created_at=datetime.now(UTC)))


async def remove_from_wishlist(db: AsyncSession, user: User, product_id: str) -> None:
    from app.modules.customers.models import WishlistItem

    wl = await _get_wishlist(db, user)
    item = await db.scalar(
        select(WishlistItem).where(
            WishlistItem.wishlist_id == wl.id, WishlistItem.product_id == uuid.UUID(product_id)
        )
    )
    if item:
        await db.delete(item)
