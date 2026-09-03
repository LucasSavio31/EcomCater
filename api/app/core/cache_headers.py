"""`Cache-Control` em respostas GET públicas (catálogo, tema, menus, mídia).

O conteúdo muda pouco e a invalidação de verdade é por tag no Next
(`POST /api/revalidate` quando o admin salva). Aqui só abrimos uma janela
curta para proxy / navegador / CDN reaproveitarem a resposta.

Nunca cacheia requisição autenticada (header `Authorization`).
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# (prefixo do path, valor de Cache-Control)
_RULES: tuple[tuple[str, str], ...] = (
    ("/media/", "public, max-age=86400, stale-while-revalidate=604800"),
    ("/static/", "public, max-age=86400, stale-while-revalidate=604800"),
    ("/api/products", "public, s-maxage=60, stale-while-revalidate=300"),
    ("/api/categories", "public, s-maxage=120, stale-while-revalidate=600"),
    ("/api/theme", "public, s-maxage=60, stale-while-revalidate=300"),
    ("/api/menus", "public, s-maxage=120, stale-while-revalidate=600"),
    ("/api/banners", "public, s-maxage=120, stale-while-revalidate=600"),
    ("/api/analytics/config", "public, s-maxage=120, stale-while-revalidate=600"),
)


class PublicCacheHeaders:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        cc = next((v for p, v in _RULES if path.startswith(p)), None)
        if cc is None:
            await self.app(scope, receive, send)
            return

        if any(k == b"authorization" for k, _ in scope.get("headers") or []):
            await self.app(scope, receive, send)
            return

        is_media = path.startswith(("/media/", "/static/"))

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and 200 <= message["status"] < 300:
                headers = message.setdefault("headers", [])
                if not any(k.lower() == b"cache-control" for k, _ in headers):
                    headers.append((b"cache-control", cc.encode()))
                    headers.append((b"vary", b"Accept-Encoding"))
                if is_media and not any(k.lower() == b"x-robots-tag" for k, _ in headers):
                    # mídia fora do índice de imagens dos buscadores / crawlers de IA
                    headers.append((b"x-robots-tag", b"noimageindex, noai, noimageai"))
            await send(message)

        await self.app(scope, receive, send_wrapper)
