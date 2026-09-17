"""Autenticação da REST API do WooCommerce: Basic Auth com Consumer
Key/Secret (o jeito documentado pra HTTPS -- `curl -u ck:cs ...`), com
fallback pra query string (`?consumer_key=&consumer_secret=`), que também é
válido no WooCommerce de verdade e alguns clientes preferem."""
from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AuthError, ForbiddenError
from app.core.security import verify_password
from app.modules.woocommerce.models import WooKey

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _parse_basic_auth(header: str) -> tuple[str, str] | None:
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    key, _, secret = decoded.partition(":")
    return key, secret


async def require_wc_auth(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> WooKey:
    creds = None
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        creds = _parse_basic_auth(auth_header)
    if creds is None:
        qs = request.query_params
        if qs.get("consumer_key") and qs.get("consumer_secret"):
            creds = (qs["consumer_key"], qs["consumer_secret"])
    if creds is None:
        raise AuthError("Consumer key/secret ausente.")

    consumer_key, consumer_secret = creds
    key_row = await db.scalar(select(WooKey).where(WooKey.consumer_key == consumer_key))
    if not key_row or not verify_password(consumer_secret, key_row.consumer_secret_hash):
        raise AuthError("Consumer key/secret inválido.")

    if request.method in _WRITE_METHODS and key_row.permission == "read":
        raise ForbiddenError("Esta chave só tem permissão de leitura.")

    key_row.last_used_at = datetime.now(UTC)
    await db.flush()
    return key_row


WcAuthDep = Annotated[WooKey, Depends(require_wc_auth)]
