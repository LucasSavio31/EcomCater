"""Rotas administrativas do módulo `analytics`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.analytics import service
from app.modules.analytics.schemas import AnalyticsAdminConfig, AnalyticsUpdateIn
from app.modules.domains import sites

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin"))]


@router.get("", response_model=AnalyticsAdminConfig)
async def get_config(db: DbDep, _: AdminDep):
    return service.to_admin(await service.get_settings(db))


@router.put("", response_model=AnalyticsAdminConfig)
async def update_config(payload: AnalyticsUpdateIn, db: DbDep, _: EditorDep):
    row = await service.update_settings(db, payload.model_dump(exclude_unset=True))
    return service.to_admin(row)


# ------------------------------------------------------------ multi-domínio
def _seo_urls(host: str | None) -> dict:
    """URLs de SEO próprias do domínio (o que se cadastra no Search Console /
    Merchant Center DESTE domínio)."""
    from app.core.config import settings

    site = f"https://{host}" if host else settings.site_url.rstrip("/")
    api = f"https://api.{host}" if host else settings.public_api_url.rstrip("/")
    return {
        "site_url": site,
        "sitemap_url": f"{site}/sitemap.xml",
        "robots_url": f"{site}/robots.txt",
        "llms_url": f"{site}/llms.txt",
        "feed_url": f"{api}/api/products/feed/google-merchant.xml",
    }


@router.get("/sites")
async def list_sites(db: DbDep, _: AdminDep) -> list[dict]:
    """Um bloco por domínio conectado (principal primeiro): tags, verificação,
    SEO e URLs de SEO de cada um -- a tela de Rastreamento mostra em acordeão."""
    from sqlalchemy import select

    from app.modules.domains.models import Domain

    await sites.refresh(force=True)
    primary = sites.primary_host()
    domains = list(await db.scalars(select(Domain).order_by(Domain.created_at)))
    out = [{
        "hostname": primary,
        "is_primary": True,
        "status": "active",
        "config": service.to_admin(await service.get_settings(db)),
        "seo_urls": _seo_urls(primary),
    }]
    for d in domains:
        if d.hostname.lower() == primary:
            continue
        row = await service.get_for_site(db, d.hostname) if d.hostname.lower() in sites.snapshot()["hosts"]             else service._empty_site_row(d.hostname.lower())
        out.append({
            "hostname": d.hostname.lower(),
            "is_primary": False,
            "status": d.status,
            "config": service.to_admin(row),
            "seo_urls": _seo_urls(d.hostname.lower()),
        })
    return out


@router.put("/sites/{hostname}", response_model=AnalyticsAdminConfig)
async def update_site(hostname: str, payload: AnalyticsUpdateIn, db: DbDep, _: EditorDep):
    from app.core.errors import NotFoundError

    await sites.refresh(force=True)
    host = hostname.strip().lower()
    if host != sites.primary_host() and host not in sites.snapshot()["hosts"]:
        raise NotFoundError("Domínio não está ativo em Infraestrutura → Domínios.")
    row = await service.update_settings(db, payload.model_dump(exclude_unset=True), host=host)
    return service.to_admin(row)
