"""Hash de senha (argon2) + emissão/verificação de JWT (access + refresh).

Tokens de cliente e de admin usam o mesmo mecanismo, mas com claim `scope`
distinto (`customer` | `admin`) — as dependências de auth exigem o scope certo.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()

Scope = Literal["customer", "admin"]
TokenType = Literal["access", "refresh"]


def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _ph.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.api_secret_key, algorithm=settings.jwt_algorithm)


def create_token(
    subject: str,
    *,
    scope: Scope,
    token_type: TokenType,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Retorna (token, jti, expiração)."""
    ttl = (
        settings.jwt_access_ttl_seconds
        if token_type == "access"
        else settings.jwt_refresh_ttl_seconds
    )
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=ttl)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "scope": scope,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if extra:
        payload.update(extra)
    return _encode(payload), jti, exp


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.api_secret_key, algorithms=[settings.jwt_algorithm])


def issue_pair(subject: str, *, scope: Scope, extra: dict[str, Any] | None = None):
    """Access + refresh de uma vez. Retorna dict pronto pra resposta + jti do refresh."""
    access, _, access_exp = create_token(
        subject, scope=scope, token_type="access", extra=extra
    )
    refresh, refresh_jti, refresh_exp = create_token(
        subject, scope=scope, token_type="refresh"
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_ttl_seconds,
        "_access_exp": access_exp,
        "_refresh_jti": refresh_jti,
        "_refresh_exp": refresh_exp,
    }
