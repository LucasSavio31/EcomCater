"""Regra de negócio do módulo `admin`: autenticação administrativa e usuários."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import (
    decode_token,
    hash_password,
    issue_pair,
    needs_rehash,
    verify_password,
)
from app.modules.admin.models import AdminUser, AuthRefreshToken

VALID_ROLES = {"super_admin", "admin", "staff"}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _store_refresh(db: AsyncSession, admin_id: str, pair: dict) -> None:
    db.add(
        AuthRefreshToken(
            subject_type="admin",
            subject_id=str(admin_id),
            jti=pair["_refresh_jti"],
            token_hash=_hash_token(pair["refresh_token"]),
            expires_at=pair["_refresh_exp"],
            created_at=datetime.now(UTC),
        )
    )


async def authenticate(db: AsyncSession, email: str, password: str) -> tuple[AdminUser, dict]:
    admin = await db.scalar(select(AdminUser).where(AdminUser.email == email))
    if not admin or not admin.is_active or not verify_password(password, admin.password_hash):
        raise AuthError("E-mail ou senha inválidos.")
    if needs_rehash(admin.password_hash):
        admin.password_hash = hash_password(password)
    admin.last_login_at = datetime.now(UTC)
    pair = issue_pair(str(admin.id), scope="admin", extra={"role": admin.role})
    await _store_refresh(db, str(admin.id), pair)
    return admin, pair


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("Refresh token inválido.") from exc
    if payload.get("type") != "refresh" or payload.get("scope") != "admin":
        raise AuthError("Refresh token inválido.")
    row = await db.scalar(
        select(AuthRefreshToken).where(AuthRefreshToken.jti == payload["jti"])
    )
    if not row or row.revoked_at is not None:
        raise AuthError("Sessão expirada. Faça login novamente.")
    row.revoked_at = datetime.now(UTC)  # rotação
    admin = await db.get(AdminUser, uuid.UUID(payload["sub"]))
    if not admin or not admin.is_active:
        raise AuthError("Admin inativo.")
    pair = issue_pair(str(admin.id), scope="admin", extra={"role": admin.role})
    await _store_refresh(db, str(admin.id), pair)
    return pair


async def logout(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except Exception:  # noqa: BLE001
        return
    row = await db.scalar(
        select(AuthRefreshToken).where(AuthRefreshToken.jti == payload.get("jti"))
    )
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)


async def change_password(
    db: AsyncSession, admin: AdminUser, current: str, new: str
) -> None:
    if not verify_password(current, admin.password_hash):
        raise AuthError("Senha atual incorreta.")
    if current == new:
        raise ValidationError("A nova senha deve ser diferente da atual.")
    admin.password_hash = hash_password(new)
    admin.must_change_password = False


async def list_admins(db: AsyncSession) -> list[AdminUser]:
    return list(await db.scalars(select(AdminUser).order_by(AdminUser.created_at)))


async def create_admin(
    db: AsyncSession, *, actor: AdminUser, email: str, name: str, password: str, role: str
) -> AdminUser:
    if actor.role != "super_admin":
        raise ForbiddenError("Só o super admin cria usuários administrativos.")
    if role not in VALID_ROLES:
        raise ValidationError(f"Papel inválido: {role}")
    if await db.scalar(select(AdminUser).where(AdminUser.email == email)):
        raise ConflictError("Já existe um admin com esse e-mail.")
    admin = AdminUser(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role=role,
        must_change_password=True,
    )
    db.add(admin)
    await db.flush()
    return admin


async def update_admin(
    db: AsyncSession, *, actor: AdminUser, admin_id: str, data: dict
) -> AdminUser:
    if actor.role != "super_admin":
        raise ForbiddenError("Só o super admin edita usuários administrativos.")
    admin = await db.get(AdminUser, uuid.UUID(admin_id))
    if not admin:
        raise NotFoundError("Admin não encontrado.")
    if "name" in data and data["name"] is not None:
        admin.name = data["name"]
    if data.get("role"):
        if data["role"] not in VALID_ROLES:
            raise ValidationError(f"Papel inválido: {data['role']}")
        admin.role = data["role"]
    if "is_active" in data and data["is_active"] is not None:
        admin.is_active = data["is_active"]
    if data.get("password"):
        admin.password_hash = hash_password(data["password"])
        admin.must_change_password = True
    return admin
