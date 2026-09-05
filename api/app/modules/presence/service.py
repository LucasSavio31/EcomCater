"""Presença "ao vivo": cada visitante = uma chave Redis com TTL curto,
renovada a cada heartbeat do front. Sem heartbeat por `PRESENCE_TTL`
segundos, o visitante simplesmente some — sem faxina nem índice separado."""
from __future__ import annotations

import json
import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.modules.presence import geoip
from app.modules.products.models import Product

PRESENCE_TTL = 90
_PREFIX = "presence:v:"

_FRIENDLY_PATHS = {
    "/": "Página inicial",
    "/carrinho": "Carrinho",
    "/checkout": "Checkout",
    "/busca": "Busca",
}


def _device_from_ua(ua: str | None) -> str:
    """Classificação simples de dispositivo a partir do User-Agent — só o
    suficiente pra mostrar um rótulo útil na lista de visitantes."""
    u = (ua or "").lower()
    if "ipad" in u:
        return "iPad"
    if "iphone" in u:
        return "iPhone"
    if "android" in u:
        return "Android"
    if "macintosh" in u or "mac os" in u:
        return "Mac"
    if "windows" in u:
        return "PC"
    if "linux" in u:
        return "Linux"
    return "Outro"


async def record(visitor_id: str, ip: str | None, path: str, user_agent: str | None = None) -> None:
    geo = await geoip.lookup(ip) or {}
    data = {
        **geo,
        "path": path,
        "ip": ip,
        "device": _device_from_ua(user_agent),
        "last_seen": time.time(),
    }
    await redis_client.set(f"{_PREFIX}{visitor_id}", json.dumps(data), ex=PRESENCE_TTL)


async def _page_labels(db: AsyncSession, paths: set[str]) -> dict[str, str]:
    """Resolve `/produto/<slug>` pro nome do produto (uma query em lote)."""
    slugs = {p.split("/produto/", 1)[1].split("/")[0].split("?")[0] for p in paths if p.startswith("/produto/")}
    slugs.discard("")
    if not slugs:
        return {}
    rows = await db.execute(select(Product.slug, Product.name).where(Product.slug.in_(slugs)))
    return {f"/produto/{slug}": name for slug, name in rows.all()}


async def list_active(db: AsyncSession) -> dict:
    now = time.time()
    visitors: list[dict] = []
    async for key in redis_client.scan_iter(match=f"{_PREFIX}*"):
        raw = await redis_client.get(key)
        if not raw:
            continue
        try:
            visitors.append(json.loads(raw))
        except ValueError:
            continue

    labels = await _page_labels(db, {v.get("path") or "" for v in visitors})
    out = []
    for v in visitors:
        path = v.get("path") or "/"
        out.append(
            {
                "country": v.get("country"),
                "country_code": v.get("country_code"),
                "region": v.get("region"),
                "city": v.get("city"),
                "lat": v.get("lat"),
                "lon": v.get("lon"),
                "path": path,
                "page_label": labels.get(path) or _FRIENDLY_PATHS.get(path) or path,
                "ip": v.get("ip"),
                "device": v.get("device"),
                "since_seconds": max(0, int(now - (v.get("last_seen") or now))),
            }
        )

    counts = Counter(v["region"] for v in out if v.get("region"))
    top_states = [{"region": r, "count": c} for r, c in counts.most_common(10)]
    return {"total": len(out), "visitors": out, "top_states": top_states}
