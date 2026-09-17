"""Rotas administrativas do módulo `woocommerce`: gerar/revogar chaves da
API REST e listar os webhooks que o ERP registrou."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.core.errors import ValidationError
from app.modules.admin.models import AdminUser
from app.modules.woocommerce import service
from app.modules.woocommerce.models import PERMISSIONS, WooKey

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin"))]


class KeyIn(BaseModel):
    description: str | None = None
    permission: str = "read_write"


def _key_out(row: WooKey) -> dict:
    return {
        "id": str(row.id),
        "consumer_key": row.consumer_key,
        "description": row.description,
        "permission": row.permission,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "created_at": row.created_at.isoformat(),
    }


@admin_router.get("/keys")
async def list_keys(db: DbDep, _: EditorDep) -> list[dict]:
    rows = await service.list_keys(db)
    return [_key_out(r) for r in rows]


@admin_router.post("/keys")
async def create_key(body: KeyIn, db: DbDep, _: EditorDep) -> dict:
    if body.permission not in PERMISSIONS:
        raise ValidationError(f"Permissão inválida: {body.permission}.")
    row, consumer_key, consumer_secret = await service.generate_key(
        db, description=body.description, permission=body.permission
    )
    await db.commit()
    # única vez que o consumer_secret aparece em texto puro -- igual o
    # WooCommerce de verdade, que também só mostra na hora da criação.
    return {**_key_out(row), "consumer_key": consumer_key, "consumer_secret": consumer_secret}


@admin_router.delete("/keys/{key_id}")
async def revoke_key(key_id: str, db: DbDep, _: EditorDep) -> dict:
    await service.revoke_key(db, key_id)
    await db.commit()
    return {"ok": True}


@admin_router.get("/webhooks")
async def list_webhooks(db: DbDep, _: EditorDep) -> list[dict]:
    rows = await service.list_webhooks(db)
    return [service.webhook_out(r) for r in rows]
