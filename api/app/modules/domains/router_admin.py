"""Rotas administrativas do módulo `domains`: credenciais + domínios.

Tudo aqui é restrito a `super_admin` (não `admin` comum) — dá controle sobre
o proxy reverso público do servidor, é bem mais sensível que um token de
frete/pagamento.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.core.errors import NotFoundError
from app.modules.admin.models import AdminUser
from app.modules.domains import service
from app.modules.domains.cache_rules import CACHE_PAGE_DEFS
from app.modules.domains.models import Domain
from app.modules.domains.schemas import (
    CachePageOut,
    CachePagesIn,
    DomainIn,
    DomainOut,
    DomainsConfigIn,
)

admin_router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
SuperDep = Annotated[AdminUser, Depends(require_role("super_admin"))]


def _domain_out(d: Domain) -> DomainOut:
    return DomainOut(
        id=str(d.id),
        hostname=d.hostname,
        is_primary=d.is_primary,
        status=d.status,
        dns_managed_by_cloudflare=d.dns_managed_by_cloudflare,
        ssl_status=d.ssl_status,
        last_error=d.last_error,
        last_checked_at=d.last_checked_at.isoformat() if d.last_checked_at else None,
        admin_hostname=service.admin_hostname(d.hostname),
        api_hostname=service.api_hostname(d.hostname),
        cloudflare_nameservers=d.cloudflare_nameservers,
        dns_confirmed=d.dns_confirmed_at is not None,
        cache_pages=d.cache_pages or [],
        cache_applied_at=d.cache_applied_at.isoformat() if d.cache_applied_at else None,
        switch_requested_at=d.switch_requested_at.isoformat() if d.switch_requested_at else None,
    )


def _config_out(cfg, domains: list[Domain]) -> dict:
    return {
        "has_aapanel": bool(cfg.aapanel_url and cfg.aapanel_api_key),
        "has_cloudflare": bool(cfg.cloudflare_api_token),
        "aapanel_url": cfg.aapanel_url,
        "server_ip": cfg.server_ip,
        "domains": [_domain_out(d) for d in domains],
        "cache_page_options": [
            CachePageOut(key=k, label=v.label, description=v.description, ttl_seconds=v.ttl_seconds)
            for k, v in CACHE_PAGE_DEFS.items()
        ],
    }


@admin_router.get("")
async def get_state(db: DbDep, _: SuperDep) -> dict:
    cfg = await service.load_config(db)
    domains = await service.list_domains(db)
    return _config_out(cfg, domains)


@admin_router.put("/credentials")
async def update_credentials(body: DomainsConfigIn, db: DbDep, _: SuperDep) -> dict:
    cfg = await service.save_config(db, body.model_dump(exclude_unset=True))
    domains = await service.list_domains(db)
    return _config_out(cfg, domains)


@admin_router.post("/credentials/test")
async def test_credentials(body: DomainsConfigIn, db: DbDep, _: SuperDep) -> dict:
    """Testa as credenciais (as do formulário, ou as já salvas se deixadas em
    branco) contra a API de verdade — não salva nada."""
    return await service.test_connection(db, body.model_dump(exclude_unset=True))


@admin_router.post("")
async def add_or_update_domain(body: DomainIn, db: DbDep, _: SuperDep) -> DomainOut:
    domain = await service.upsert_domain(db, body.hostname)
    await service.provision(db, domain)
    return _domain_out(domain)


@admin_router.post("/{domain_id}/retry")
async def retry_domain(domain_id: str, db: DbDep, _: SuperDep) -> DomainOut:
    domain = await service.get_domain(db, domain_id)
    if not domain:
        raise NotFoundError("Domínio não encontrado.")
    await service.provision(db, domain)
    return _domain_out(domain)


@admin_router.post("/{domain_id}/set-primary")
async def set_primary_domain(domain_id: str, db: DbDep, _: SuperDep) -> DomainOut:
    """Torna este o domínio principal -- pede a troca das variáveis do site
    (`.env`) + rebuild do front/admin sozinho (arquivo-gatilho, aplicado por
    um script no servidor em até alguns minutos)."""
    domain = await service.get_domain(db, domain_id)
    if not domain:
        raise NotFoundError("Domínio não encontrado.")
    domain = await service.set_primary(db, domain)
    return _domain_out(domain)


@admin_router.put("/{domain_id}/cache")
async def update_cache_pages(domain_id: str, body: CachePagesIn, db: DbDep, _: SuperDep) -> DomainOut:
    domain = await service.get_domain(db, domain_id)
    if not domain:
        raise NotFoundError("Domínio não encontrado.")
    await service.apply_cache_pages(db, domain, body.pages)
    return _domain_out(domain)


@admin_router.post("/{domain_id}/purge-cache")
async def purge_domain_cache(domain_id: str, db: DbDep, _: SuperDep) -> dict:
    domain = await service.get_domain(db, domain_id)
    if not domain:
        raise NotFoundError("Domínio não encontrado.")
    await service.purge_cache(db, domain)
    return {"ok": True}


@admin_router.delete("/{domain_id}")
async def remove_domain(domain_id: str, db: DbDep, _: SuperDep) -> dict:
    domain = await service.get_domain(db, domain_id)
    if not domain:
        raise NotFoundError("Domínio não encontrado.")
    await service.delete_domain(db, domain)
    return {"ok": True}
