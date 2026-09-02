"""Invalida o cache de leitura (Redis) quando o admin salva algo público.

Qualquer POST/PUT/PATCH/DELETE bem-sucedido nas rotas de catálogo do
admin dá um ``bump`` no(s) namespace(s) correspondente(s) — a próxima
leitura da loja já recalcula. Simples e sem risco de servir dado velho.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.cache import bump

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# (prefixo do path admin, namespaces a invalidar)
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/api/admin/products", ("catalog", "product")),
    ("/api/admin/categories", ("catalog", "product")),
    ("/api/admin/banners", ("catalog",)),
    ("/api/admin/menus", ("menus",)),
    ("/api/admin/theme", ("theme", "content")),
    # nome da loja / CNPJ / redes sociais entram no payload de /api/theme
    ("/api/admin/settings", ("theme",)),
)


class CacheBust:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in _WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        nss = next((ns for p, ns in _RULES if path.startswith(p)), None)
        if nss is None:
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
            await bump(*nss)
