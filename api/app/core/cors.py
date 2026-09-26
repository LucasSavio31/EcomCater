"""CORS que também libera, sem reiniciar, a loja/admin/API de todo domínio
ativo em Infraestrutura → Domínios (multi-domínio -- ver
`app/modules/domains/sites.py`). As origens fixas do `.env` (CORS_ORIGINS)
continuam valendo."""
from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

from app.modules.domains import sites


class SitesCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            await sites.refresh()
        await super().__call__(scope, receive, send)

    def is_allowed_origin(self, origin: str) -> bool:
        return super().is_allowed_origin(origin) or sites.is_known_origin(origin)
