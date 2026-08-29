"""Rota pública mínima do tema — consumida por SSR no frontend (Fase 1).

O CRUD de aparência completo entra na Fase 7/8 (`router_admin.py`).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.theme.models import ThemeSettings

router = APIRouter()


@router.get("")
async def get_theme(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    row = await db.get(ThemeSettings, 1)
    if not row:
        return {
            "primary_color": "#111111",
            "secondary_color": "#4B5563",
            "accent_color": "#DC2626",
            "text_color": "#111827",
            "bg_color": "#FFFFFF",
            "font_family": "Inter, system-ui, sans-serif",
            "logo_url": None,
            "top_bar_enabled": False,
            "top_bar_message": None,
        }
    return {c.name: getattr(row, c.name) for c in ThemeSettings.__table__.columns}
