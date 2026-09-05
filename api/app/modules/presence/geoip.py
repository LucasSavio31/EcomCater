"""Geolocalização por IP via ip-api.com (gratuito, sem chave).

Cache em Redis por IP evita repetir a chamada a cada heartbeat (~25s) e
respeita o limite de 45 req/min do plano gratuito. Falha do serviço externo
também fica em cache por um tempo curto, pra não martelar ele fora do ar.
"""
from __future__ import annotations

import ipaddress
import json
import logging

import httpx

from app.core.redis import redis_client

logger = logging.getLogger("presence.geoip")

_CACHE_TTL = 6 * 3600
_FAIL_TTL = 5 * 60
_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,lat,lon"


def _is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


async def lookup(ip: str | None) -> dict | None:
    """`None` para IP ausente/privado (dev local) ou quando a geolocalização falha."""
    if not ip or not _is_public(ip):
        return None
    key = f"presence:geo:{ip}"
    cached = await redis_client.get(key)
    if cached == "err":
        return None
    if cached:
        try:
            return json.loads(cached)
        except ValueError:
            pass

    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(_URL.format(ip=ip))
        data = r.json()
    except Exception:  # noqa: BLE001
        logger.debug("geoip falhou para %s", ip, exc_info=True)
        await redis_client.set(key, "err", ex=_FAIL_TTL)
        return None

    if data.get("status") != "success":
        await redis_client.set(key, "err", ex=_FAIL_TTL)
        return None

    out = {
        "country": data.get("country") or None,
        "country_code": (data.get("countryCode") or "").upper() or None,
        "region": data.get("regionName") or None,
        "city": data.get("city") or None,
        "lat": data.get("lat"),
        "lon": data.get("lon"),
    }
    await redis_client.set(key, json.dumps(out), ex=_CACHE_TTL)
    return out
