"""Multi-domínio: a mesma loja respondendo em vários domínios ao mesmo tempo,
cada um com as próprias URLs (canonical, sitemap, feed, links de e-mail).

Cada domínio ATIVO em Infraestrutura → Domínios vira um "site": a loja em
`<host>`, o admin em `admin.<host>` e a API em `api.<host>` (vhosts criados
pelo `service.provision`). O domínio principal continua sendo o do `.env`
(`SITE_URL`) -- é o fallback quando a requisição não diz de qual site veio.

A lista de hosts ativos fica em memória por `_TTL` segundos (lida do banco
sob demanda) -- CORS e resolução de origem rodam em toda requisição, não dá
pra ir no banco toda vez.
"""
from __future__ import annotations

import time
from urllib.parse import urlsplit

from sqlalchemy import select

from app.core.config import settings

_TTL = 60.0
_cache: dict = {"at": 0.0, "hosts": frozenset(), "primary": None}


def _norm(host: str | None) -> str | None:
    """'https://WWW.Loja.com:443/x' | 'loja.com' -> 'www.loja.com' (sem porta)."""
    if not host:
        return None
    raw = host.strip().lower()
    if "://" in raw:
        raw = urlsplit(raw).hostname or ""
    return raw.split(":")[0].strip(".") or None


def site_of(host: str | None) -> str | None:
    """Host da LOJA a partir de qualquer host do site: `loja.com`,
    `www.loja.com`, `api.loja.com`, `admin.loja.com` -> `loja.com`, se for um
    domínio ativo. `None` se não for (IP, localhost, host desconhecido)."""
    h = _norm(host)
    if not h:
        return None
    hosts = _cache["hosts"]
    if h in hosts:
        return h
    for prefix in ("www.", "api.", "admin."):
        if h.startswith(prefix) and h[len(prefix):] in hosts:
            return h[len(prefix):]
    return None


def site_url(host: str | None) -> str:
    """URL pública da loja do site `host` -- cai no `SITE_URL` (principal)."""
    site = site_of(host)
    return f"https://{site}" if site else settings.site_url.rstrip("/")


def default_host() -> str | None:
    """Host do domínio principal (o do `.env`, `SITE_URL`)."""
    return _norm(settings.site_url)


def primary_host() -> str | None:
    """Domínio principal: o marcado em Infraestrutura → Domínios, senão o do .env."""
    return _cache["primary"] or default_host()


def request_site(request) -> str | None:
    """Site de onde veio a requisição: `Origin` (chamada do navegador pela
    loja) > `Referer` > `Host` (ex.: feed pedido em `api.<site>`)."""
    h = request.headers
    for raw in (h.get("origin"), h.get("referer")):
        site = site_of(raw)
        if site:
            return site
    fwd = (h.get("x-forwarded-host") or "").split(",")[0].strip()
    return site_of(fwd or h.get("host"))


def request_site_url(request) -> str:
    return site_url(request_site(request))


def is_known_origin(origin: str) -> bool:
    """CORS: loja/admin/api de qualquer domínio ativo (só HTTPS)."""
    if not origin.lower().startswith("https://"):
        return False
    return site_of(origin) is not None


def snapshot() -> dict:
    return {
        "primary": _cache["primary"],
        "hosts": sorted(_cache["hosts"]),
    }


async def refresh(force: bool = False) -> None:
    """Relê os domínios ativos do banco se o cache venceu. Nunca levanta --
    banco fora do ar mantém a última lista conhecida."""
    now = time.monotonic()
    if not force and now - _cache["at"] < _TTL:
        return
    _cache["at"] = now  # marca antes: requisições concorrentes não disparam N leituras
    try:
        from app.core.database import SessionLocal
        from app.modules.domains.models import STATUS_ACTIVE, Domain

        async with SessionLocal() as db:
            rows = (
                await db.execute(
                    select(Domain.hostname, Domain.is_primary).where(
                        Domain.status == STATUS_ACTIVE
                    )
                )
            ).all()
        _cache["hosts"] = frozenset(r.hostname.lower() for r in rows)
        _cache["primary"] = next((r.hostname.lower() for r in rows if r.is_primary), None)
    except Exception:  # noqa: BLE001 -- CORS/links não podem derrubar a requisição
        import logging

        logging.getLogger(__name__).warning("sites: falha ao ler domínios ativos", exc_info=True)


def invalidate() -> None:
    """Chamar depois de ativar/remover/editar um domínio (vale na hora)."""
    _cache["at"] = 0.0
