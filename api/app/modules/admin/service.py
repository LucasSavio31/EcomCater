"""Regra de negócio do módulo `admin`: autenticação administrativa e usuários."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    issue_pair,
    needs_rehash,
    verify_password,
)
from app.modules.admin import twofa
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


async def verify_credentials(db: AsyncSession, email: str, password: str) -> AdminUser:
    admin = await db.scalar(select(AdminUser).where(AdminUser.email == email))
    if not admin or not admin.is_active or not verify_password(password, admin.password_hash):
        raise AuthError("E-mail ou senha inválidos.")
    if needs_rehash(admin.password_hash):
        admin.password_hash = hash_password(password)
    return admin


async def issue_session(db: AsyncSession, admin: AdminUser) -> dict:
    admin.last_login_at = datetime.now(UTC)
    pair = issue_pair(str(admin.id), scope="admin", extra={"role": admin.role})
    await _store_refresh(db, str(admin.id), pair)
    return pair


async def authenticate(db: AsyncSession, email: str, password: str) -> tuple[AdminUser, dict]:
    admin = await verify_credentials(db, email, password)
    return admin, await issue_session(db, admin)


def mfa_challenge_token(admin_id: str) -> str:
    """Token curto emitido após a senha, trocado por sessão real com o código 2FA."""
    token, _, _ = create_token(
        str(admin_id), scope="admin_mfa", token_type="access", extra={"mfa_pending": True}
    )
    return token


async def resolve_mfa_challenge(db: AsyncSession, mfa_token: str, code: str) -> tuple[AdminUser, dict]:
    try:
        payload = decode_token(mfa_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("Sessão de verificação expirada. Faça login de novo.") from exc
    if payload.get("scope") != "admin_mfa" or not payload.get("mfa_pending"):
        raise AuthError("Token de verificação inválido.")
    admin = await db.get(AdminUser, uuid.UUID(payload["sub"]))
    if not admin or not admin.is_active:
        raise AuthError("Conta inativa.")
    if not check_2fa(admin, code):
        raise AuthError("Código de verificação inválido.")
    return admin, await issue_session(db, admin)


# --------------------------------------------------------------------- 2FA
async def start_2fa(db: AsyncSession, admin: AdminUser) -> dict:
    if admin.totp_enabled:
        raise ValidationError("A verificação em duas etapas já está ativa.")
    secret = twofa.new_secret()
    admin.totp_secret = secret
    await db.flush()
    uri = twofa.provisioning_uri(secret, admin.email)
    return {"secret": secret, "otpauth_uri": uri, "qr_svg": twofa.qr_svg(uri)}


async def confirm_2fa(db: AsyncSession, admin: AdminUser, code: str) -> list[str]:
    if not admin.totp_secret:
        raise ValidationError("Comece a configuração antes de confirmar.")
    if not twofa.verify_totp(admin.totp_secret, code):
        raise AuthError("Código inválido. Confira o horário do celular e tente de novo.")
    admin.totp_enabled = True
    codes = twofa.gen_recovery_codes()
    admin.recovery_codes_json = [twofa.hash_code(c) for c in codes]
    await db.flush()
    return codes


async def disable_2fa(db: AsyncSession, admin: AdminUser, password: str) -> None:
    if not verify_password(password, admin.password_hash):
        raise AuthError("Senha incorreta.")
    admin.totp_secret = None
    admin.totp_enabled = False
    admin.recovery_codes_json = []
    await db.flush()


def check_2fa(admin: AdminUser, code: str) -> bool:
    if twofa.verify_totp(admin.totp_secret, code):
        return True
    h = twofa.hash_code(code)
    codes = list(admin.recovery_codes_json or [])
    if h in codes:
        codes.remove(h)  # código de recuperação é de uso único
        admin.recovery_codes_json = codes
        return True
    return False


async def update_own_profile(db: AsyncSession, admin: AdminUser, name: str | None, email: str | None) -> AdminUser:
    if name and name.strip():
        admin.name = name.strip()
    if email and email.strip().lower() != admin.email.lower():
        dup = await db.scalar(
            select(AdminUser).where(AdminUser.email == email.strip(), AdminUser.id != admin.id)
        )
        if dup:
            raise ConflictError("Já existe outra conta com esse e-mail.")
        admin.email = email.strip()
    await db.flush()
    return admin


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
