"""Dependências de autenticação/autorização e gate de módulo."""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AuthError, ForbiddenError, ModuleDisabledError
from app.core.security import decode_token
from app.modules.admin.models import AdminUser, ModuleRow
from app.modules.customers.models import User

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Credenciais ausentes.")
    return authorization.split(" ", 1)[1].strip()


async def _decode(authorization: str | None, expected_scope: str) -> dict:
    token = _bearer(authorization)
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("Token inválido ou expirado.") from exc
    if payload.get("type") != "access":
        raise AuthError("Tipo de token inválido.")
    if payload.get("scope") != expected_scope:
        raise ForbiddenError("Escopo de token incorreto.")
    return payload


async def get_current_customer(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    payload = await _decode(authorization, "customer")
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise AuthError("Usuário não encontrado ou inativo.")
    return user


async def get_current_customer_optional(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    if not authorization:
        return None
    try:
        return await get_current_customer(db, authorization)
    except (AuthError, ForbiddenError):
        return None


async def get_current_admin(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminUser:
    payload = await _decode(authorization, "admin")
    admin = await db.get(AdminUser, uuid.UUID(payload["sub"]))
    if not admin or not admin.is_active:
        raise AuthError("Admin não encontrado ou inativo.")
    return admin


async def get_current_admin_downloadable(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> AdminUser:
    """Igual a get_current_admin, mas aceita o access token também por `?token=`
    — para links de download/impressão abertos direto no navegador (sem header)."""
    auth = authorization or (f"Bearer {token}" if token else None)
    payload = await _decode(auth, "admin")
    admin = await db.get(AdminUser, uuid.UUID(payload["sub"]))
    if not admin or not admin.is_active:
        raise AuthError("Admin não encontrado ou inativo.")
    return admin


def require_role(*roles: str) -> Callable:
    async def _dep(admin: Annotated[AdminUser, Depends(get_current_admin)]) -> AdminUser:
        if admin.role not in roles and admin.role != "super_admin":
            raise ForbiddenError("Permissão insuficiente.")
        return admin

    return _dep


def require_module_enabled(slug: str) -> Callable:
    async def _dep(db: DbDep) -> None:
        row = await db.get(ModuleRow, slug)
        if row is not None and row.enabled is False:
            raise ModuleDisabledError(f"Módulo '{slug}' está desabilitado.")

    return _dep


async def get_module_config(db: AsyncSession, slug: str) -> dict:
    row = await db.get(ModuleRow, slug)
    return dict(row.config_json) if row and row.config_json else {}
