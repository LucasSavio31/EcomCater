"""Tokens de redefinição de senha (cliente e admin).

O token cru vai só no link do e-mail; no banco guardamos apenas o SHA-256.
Uso único, expira em `ttl_minutes`. Ao criar um novo, os pendentes do mesmo
sujeito são invalidados.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import PasswordReset


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_reset(
    db: AsyncSession,
    subject_type: str,
    subject_id: str,
    *,
    ttl_minutes: int = 30,
    ip: str | None = None,
) -> str:
    now = datetime.now(UTC)
    # invalida pendentes anteriores do mesmo sujeito
    await db.execute(
        update(PasswordReset)
        .where(
            PasswordReset.subject_type == subject_type,
            PasswordReset.subject_id == str(subject_id),
            PasswordReset.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordReset(
            subject_type=subject_type,
            subject_id=str(subject_id),
            token_hash=_hash(raw),
            expires_at=now + timedelta(minutes=ttl_minutes),
            requested_ip=(ip or None),
            created_at=now,
        )
    )
    await db.flush()
    return raw


async def consume_reset(db: AsyncSession, raw_token: str) -> tuple[str, str] | None:
    """Valida e QUEIMA o token. Devolve (subject_type, subject_id) ou None."""
    if not raw_token:
        return None
    row = await db.scalar(
        select(PasswordReset).where(PasswordReset.token_hash == _hash(raw_token))
    )
    if row is None:
        return None
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if row.used_at is not None or expires_at < datetime.now(UTC):
        return None
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.id == row.id)
        .values(used_at=datetime.now(UTC))
    )
    return row.subject_type, row.subject_id
