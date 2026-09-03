"""Avisa o Next (loja) para revalidar as tags de cache do SSR.

Best-effort: chamado pelo middleware `CacheBust` depois de um write no admin,
junto com o bump do Redis. Se o Next não responder, tudo bem — o `revalidate`
das páginas cobre no pior caso.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("next-revalidate")


async def revalidate_tags(*tags: str) -> None:
    tags = tuple(t for t in tags if t)
    if not tags:
        return
    base = settings.site_url.rstrip("/")
    params = {"tag": ",".join(tags)}
    if settings.revalidate_secret:
        params["secret"] = settings.revalidate_secret
    try:
        async with httpx.AsyncClient(timeout=3, verify=False) as c:  # noqa: S501 (cert self-signed no IP)
            await c.post(f"{base}/api/revalidate", params=params)
    except Exception:  # noqa: BLE001
        logger.debug("revalidate do Next falhou para %s", tags, exc_info=True)
