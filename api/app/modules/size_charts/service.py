"""Regra de negócio do módulo `size_charts`."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.modules.size_charts.models import SizeChart


def _uuid(v) -> uuid.UUID:
    try:
        return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


def out(c: SizeChart) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "columns": list(c.columns or []),
        "rows": [list(r) for r in (c.rows or [])],
        "note": c.note,
    }


def _clean(data: dict) -> dict:
    cols = [str(x).strip() for x in (data.get("columns") or [])][:12]
    ncol = len(cols)
    rows = []
    for r in data.get("rows") or []:
        cells = [str(x).strip() for x in r][:ncol]
        cells += [""] * (ncol - len(cells))
        rows.append(cells)
    clean = {"columns": cols, "rows": rows[:200]}
    if "name" in data:
        clean["name"] = str(data["name"]).strip()[:120] or "Tabela de medidas"
    if "note" in data:
        clean["note"] = (str(data["note"]).strip()[:400] or None) if data["note"] else None
    return clean


async def list_all(db: AsyncSession) -> list[dict]:
    rows = await db.scalars(select(SizeChart).order_by(SizeChart.name))
    return [out(c) for c in rows]


async def get(db: AsyncSession, chart_id: str) -> SizeChart:
    c = await db.get(SizeChart, _uuid(chart_id))
    if not c:
        raise NotFoundError("Tabela de medidas não encontrada.")
    return c


async def create(db: AsyncSession, data: dict) -> SizeChart:
    d = _clean(data)
    c = SizeChart(name=d.get("name") or "Tabela de medidas",
                  columns=d["columns"], rows=d["rows"], note=d.get("note"))
    db.add(c)
    await db.flush()
    return c


async def update(db: AsyncSession, chart_id: str, data: dict) -> SizeChart:
    c = await get(db, chart_id)
    for k, v in _clean(data).items():
        setattr(c, k, v)
    await db.flush()
    return c


async def delete(db: AsyncSession, chart_id: str) -> None:
    c = await db.get(SizeChart, _uuid(chart_id))
    if c:
        await db.delete(c)
