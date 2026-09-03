"""Invalida os DOIS caches de leitura quando o admin salva algo público:
o cache Redis da API (``bump``) e as tags de SSR do Next (``/api/revalidate``).

Qualquer POST/PUT/PATCH/DELETE bem-sucedido nas rotas de catálogo/tema do
admin dispara a invalidação correspondente — a loja reflete na hora, sem
esperar o ``revalidate`` das páginas.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.cache import bump
from app.core.next_revalidate import revalidate_tags

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# (prefixo do path admin, namespaces Redis, tags do Next)
_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("/api/admin/products", ("catalog", "product"), ("products",)),
    ("/api/admin/categories", ("catalog", "product"), ("categories", "products")),
    ("/api/admin/banners", ("catalog",), ("banners",)),
    ("/api/admin/menus", ("menus",), ("menus",)),
    ("/api/admin/theme", ("theme", "content"), ("theme", "pages")),
    # nome da loja / CNPJ / redes sociais entram no payload de /api/theme
    ("/api/admin/settings", ("theme",), ("theme", "settings")),
    ("/api/admin/rastreamento", (), ("analytics",)),
    ("/api/admin/analytics", (), ("analytics",)),
)


class CacheBust:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in _WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        rule = next((r for r in _RULES if path.startswith(r[0])), None)
        if rule is None:
            await self.app(scope, receive, send)
            return

        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        if 200 <= status_code < 400:
            _prefix, redis_ns, next_tags = rule
            if redis_ns:
                await bump(*redis_ns)
            if next_tags:
                await revalidate_tags(*next_tags)
