"""`Cache-Control` em respostas GET públicas (catálogo, tema, menus, mídia).

O conteúdo muda pouco e a invalidação de verdade é por tag no Next
(`POST /api/revalidate` quando o admin salva). Aqui só abrimos uma janela
curta para proxy / navegador / CDN reaproveitarem a resposta.

Nos paths de catálogo (não mídia), também calculamos um `ETag` fraco e
respondemos `304` quando o `If-None-Match` do request já bate — barato pro
proxy/CDN revalidar sem reenviar o corpo inteiro.

Nunca cacheia requisição autenticada (header `Authorization`).
"""
from __future__ import annotations

import hashlib

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# (prefixo do path, valor de Cache-Control)
_RULES: tuple[tuple[str, str], ...] = (
    # mídia tem caminho content-addressed (pasta = uuid, nunca reescrita): uma
    # imagem nova = pasta nova. Pode cachear "para sempre" sem revalidar.
    ("/media/", "public, max-age=31536000, immutable"),
    ("/static/", "public, max-age=31536000, immutable"),
    ("/api/products", "public, s-maxage=60, stale-while-revalidate=300, stale-if-error=86400"),
    ("/api/categories", "public, s-maxage=120, stale-while-revalidate=600, stale-if-error=86400"),
    ("/api/theme", "public, s-maxage=60, stale-while-revalidate=300, stale-if-error=86400"),
    ("/api/menus", "public, s-maxage=120, stale-while-revalidate=600, stale-if-error=86400"),
    ("/api/banners", "public, s-maxage=120, stale-while-revalidate=600, stale-if-error=86400"),
    ("/api/analytics/config", "public, s-maxage=120, stale-while-revalidate=600, stale-if-error=86400"),
)

# Acima disso, não bufferiza pra calcular ETag — deixa a resposta seguir como
# hoje (sem ETag). São respostas de catálogo, tipicamente poucos KB.
_ETAG_BODY_LIMIT = 1_000_000


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

        if is_media:
            await self.app(scope, receive, self._media_send_wrapper(send, cc))
            return

        if_none_match = next(
            (v.decode("latin-1") for k, v in scope.get("headers") or [] if k == b"if-none-match"),
            None,
        )
        await self.app(scope, receive, self._etag_send_wrapper(send, cc, if_none_match))

    def _media_send_wrapper(self, send: Send, cc: str):
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and 200 <= message["status"] < 300:
                headers = message.setdefault("headers", [])
                if not any(k.lower() == b"cache-control" for k, _ in headers):
                    headers.append((b"cache-control", cc.encode()))
                    headers.append((b"vary", b"Accept-Encoding"))
                if not any(k.lower() == b"x-robots-tag" for k, _ in headers):
                    # mídia fora do índice de imagens dos buscadores / crawlers de IA
                    headers.append((b"x-robots-tag", b"noimageindex, noai, noimageai"))
            await send(message)

        return send_wrapper

    def _etag_send_wrapper(self, send: Send, cc: str, if_none_match: str | None):
        state: dict = {"start": None, "chunks": [], "size": 0, "too_big": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                state["start"] = message
                return

            if message["type"] != "http.response.body":
                await send(message)
                return

            body = message.get("body", b"")
            if not state["too_big"]:
                state["chunks"].append(body)
                state["size"] += len(body)
                if state["size"] > _ETAG_BODY_LIMIT:
                    state["too_big"] = True

            if message.get("more_body"):
                return

            await self._flush(send, cc, if_none_match, state)

        return send_wrapper

    @staticmethod
    async def _flush(send: Send, cc: str, if_none_match: str | None, state: dict) -> None:
        start = state["start"] or {"status": 200, "headers": []}
        status = start.get("status", 200)
        headers = [
            (k, v)
            for k, v in (start.get("headers") or [])
            if k.lower() not in (b"cache-control", b"vary")
        ]
        content_type = next((v for k, v in headers if k.lower() == b"content-type"), b"")
        is_json = content_type.split(b";")[0].strip() == b"application/json"

        headers.append((b"cache-control", cc.encode()))
        headers.append((b"vary", b"Accept-Encoding"))

        eligible = 200 <= status < 300 and is_json and not state["too_big"]
        body = b"".join(state["chunks"])

        if not eligible:
            await send({"type": "http.response.start", "status": status, "headers": headers})
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        etag = 'W/"' + hashlib.blake2b(body, digest_size=10).hexdigest() + '"'
        headers.append((b"etag", etag.encode()))

        if if_none_match is not None and if_none_match == etag:
            await send({"type": "http.response.start", "status": 304, "headers": headers})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body, "more_body": False})
