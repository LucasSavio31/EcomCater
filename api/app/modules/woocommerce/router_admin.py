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
    # multi-domínio: domínio da chave (vazio = principal)
    hostname: str | None = None


def _key_out(row: WooKey) -> dict:
    return {
        "id": str(row.id),
        "consumer_key": row.consumer_key,
        "description": row.description,
        "permission": row.permission,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "created_at": row.created_at.isoformat(),
        "hostname": row.hostname,
    }


@admin_router.get("/sites")
async def list_sites(db: DbDep, _: EditorDep) -> list[dict]:
    """Domínios pra tela de Integrações (acordeão por domínio): principal
    primeiro, depois os cadastrados em Infraestrutura → Domínios."""
    from sqlalchemy import select

    from app.modules.domains import sites
    from app.modules.domains.models import Domain

    await sites.refresh(force=True)
    primary = sites.primary_host()
    out = [{"hostname": primary, "is_primary": True, "status": "active"}]
    for d in await db.scalars(select(Domain).order_by(Domain.created_at)):
        if d.hostname.lower() != primary:
            out.append({"hostname": d.hostname.lower(), "is_primary": False, "status": d.status})
    return out


@admin_router.get("/keys")
async def list_keys(db: DbDep, _: EditorDep, hostname: str | None = None) -> list[dict]:
    """`hostname`: só as chaves desse domínio (vazio = principal)."""
    from app.modules.domains import sites

    await sites.refresh()
    rows = await service.list_keys(db)
    scope = service.scope_of(hostname)
    return [_key_out(r) for r in rows if service.scope_of(r.hostname) == scope]


@admin_router.post("/keys")
async def create_key(body: KeyIn, db: DbDep, _: EditorDep) -> dict:
    if body.permission not in PERMISSIONS:
        raise ValidationError(f"Permissão inválida: {body.permission}.")
    from app.modules.domains import sites

    await sites.refresh()
    row, consumer_key, consumer_secret = await service.generate_key(
        db, description=body.description, permission=body.permission, hostname=body.hostname
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
async def list_webhooks(db: DbDep, _: EditorDep, hostname: str | None = None) -> list[dict]:
    """`hostname`: só os webhooks que o ERP desse domínio registrou."""
    from app.modules.domains import sites

    await sites.refresh()
    rows = await service.list_webhooks(db, hostname)
    return [service.webhook_out(r) for r in rows]
