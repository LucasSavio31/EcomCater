"""Cache de leitura em Redis para os endpoints públicos (catálogo/tema/menus).

Como funciona
-------------
Cada *namespace* (``catalog``, ``product``, ``theme``, ``menus``, ``content``)
tem um contador de versão em Redis (``ecom:cver:{ns}``). A chave de cache
embute a versão atual — então ``bump(ns)`` invalida **tudo** do namespace
num único ``INCR``, sem ``KEYS``/``SCAN``. As chaves órfãs somem sozinhas
quando o TTL expira.

Tudo é *best-effort*: qualquer erro no Redis (ou cache desligado via
``CACHE_ENABLED=false``) cai direto no ``loader`` — o site nunca quebra
por causa do cache.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger("cache")

T = TypeVar("T")

_PREFIX = "ecom:cache"
_VER_PREFIX = "ecom:cver"

# namespaces conhecidos (só p/ documentação / uso do middleware de invalidação)
NS_CATALOG = "catalog"
NS_PRODUCT = "product"
NS_THEME = "theme"
NS_MENUS = "menus"
NS_CONTENT = "content"


def _enabled() -> bool:
    return bool(getattr(settings, "cache_enabled", True))


def _digest(parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]  # noqa: S324 (não-cripto)


async def _version(ns: str) -> str:
    try:
        v = await redis_client.get(f"{_VER_PREFIX}:{ns}")
        return str(v) if v is not None else "0"
    except Exception:  # noqa: BLE001
        return "0"


async def cached_json(
    ns: str,
    key_parts: Any,
    ttl: int,
    loader: Callable[[], Awaitable[T]],
) -> T:
    """Retorna ``loader()`` com cache JSON em Redis por ``ttl`` segundos.

    ``key_parts`` é qualquer coisa serializável (dict/list/tupla) que
    identifique unicamente a resposta — vira o hash da chave.
    """
    if not _enabled():
        return await loader()

    key: str | None = None
    try:
        ver = await _version(ns)
        key = f"{_PREFIX}:{ns}:{ver}:{_digest(key_parts)}"
        hit = await redis_client.get(key)
        if hit is not None:
            return json.loads(hit)
    except Exception:  # noqa: BLE001
        logger.debug("cache get falhou (ns=%s)", ns, exc_info=True)
        key = None

    result = await loader()

    if key is not None:
        try:
            await redis_client.set(key, json.dumps(result, default=str), ex=ttl)
        except Exception:  # noqa: BLE001
            logger.debug("cache set falhou (ns=%s)", ns, exc_info=True)

    return result


async def bump(*namespaces: str) -> None:
    """Invalida todo o cache dos namespaces informados (um ``INCR`` cada)."""
    for ns in namespaces:
        try:
            await redis_client.incr(f"{_VER_PREFIX}:{ns}")
        except Exception:  # noqa: BLE001
            logger.debug("cache bump falhou (ns=%s)", ns, exc_info=True)
