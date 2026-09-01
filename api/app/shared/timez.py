"""Limites de dia no fuso da loja (`settings.store_timezone`).

O painel filtra escolhendo um dia no calendário local. A query precisa
desses limites convertidos para UTC — senão pedidos da noite (que em UTC
caem no dia seguinte) entram/saem do filtro no dia errado.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings


def store_tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.store_timezone)
    except Exception:  # noqa: BLE001
        return ZoneInfo("America/Sao_Paulo")


def local_day_start(d: date) -> datetime:
    """00:00 do dia `d` no fuso da loja, em UTC."""
    return datetime.combine(d, time.min, tzinfo=store_tz()).astimezone(UTC)


def local_day_end(d: date) -> datetime:
    """23:59:59.999999 do dia `d` no fuso da loja, em UTC."""
    return datetime.combine(d, time.max, tzinfo=store_tz()).astimezone(UTC)


def local_today_start() -> datetime:
    """00:00 de hoje (fuso da loja), em UTC."""
    return local_day_start(datetime.now(store_tz()).date())


def parse_day_bound(raw: str | None, *, end: bool) -> datetime | None:
    """`"AAAA-MM-DD"` -> início (``end=False``) ou fim (``end=True``) do dia
    no fuso da loja, em UTC. Também aceita datetime ISO completo (normalizado
    para UTC)."""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 10:
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return None
        return local_day_end(d) if end else local_day_start(d)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(UTC)
