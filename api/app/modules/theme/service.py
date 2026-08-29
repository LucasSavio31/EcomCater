"""Regra de negócio do módulo `theme` — tema visual (singleton) + páginas."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.theme.models import Page, ThemeSettings
from app.shared.images import process_image
from app.shared.slugify import make_slug
from app.shared.storage import storage

_THEME_FIELDS = {
    "primary_color", "secondary_color", "accent_color", "text_color", "bg_color",
    "button_bg_color", "button_text_color", "button_hover_color",
    "header_bg_color", "header_text_color", "header_max_width_px",
    "footer_bg_color", "footer_text_color",
    "font_family", "free_shipping_threshold_cents", "whatsapp_number",
    "top_bar_message", "top_bar_enabled",
}


def theme_out(row: ThemeSettings) -> dict:
    return {
        **{f: getattr(row, f) for f in _THEME_FIELDS},
        "logo_url": storage.url(row.logo_key) if row.logo_key else None,
        "logo_mobile_url": storage.url(row.logo_mobile_key) if row.logo_mobile_key else None,
        "favicon_url": storage.url(row.favicon_key) if row.favicon_key else None,
    }


async def get_theme(db: AsyncSession) -> ThemeSettings:
    row = await db.get(ThemeSettings, 1)
    if not row:
        row = ThemeSettings(id=1, updated_at=datetime.now(UTC))
        db.add(row)
        await db.flush()
    return row


_COLOR_FIELDS = {f for f in _THEME_FIELDS if f.endswith("_color")}
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


async def update_theme(db: AsyncSession, data: dict) -> ThemeSettings:
    row = await get_theme(db)
    for k, v in data.items():
        if k not in _THEME_FIELDS or v is None:
            continue
        if k in _COLOR_FIELDS and not _HEX_RE.match(str(v)):
            raise ValidationError(f"Cor inválida em '{k}': use formato hexadecimal (#RRGGBB).")
        if k == "header_max_width_px":
            v = max(640, min(2560, int(v)))
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def set_theme_image(db: AsyncSession, kind: str, raw: bytes, filename: str) -> ThemeSettings:
    if kind not in ("logo", "logo_mobile", "favicon"):
        raise ValidationError("Tipo de imagem inválido.")
    row = await get_theme(db)
    processed = process_image(raw, filename, prefix="theme")
    setattr(row, f"{kind}_key", processed.medium_key if kind != "favicon" else processed.thumb_key)
    row.updated_at = datetime.now(UTC)
    return row


# --------------------------------------------------------------------- páginas
def page_out(p: Page) -> dict:
    return {
        "id": str(p.id),
        "slug": p.slug,
        "title": p.title,
        "body": p.body,
        "is_published": p.is_published,
        "seo_title": p.seo_title,
        "seo_description": p.seo_description,
    }


async def get_page(db: AsyncSession, slug: str, *, published_only: bool = True) -> Page:
    p = await db.scalar(select(Page).where(Page.slug == slug))
    if not p or (published_only and not p.is_published):
        raise NotFoundError("Página não encontrada.")
    return p


async def list_pages(db: AsyncSession) -> list[Page]:
    return list(await db.scalars(select(Page).order_by(Page.title)))


async def create_page(db: AsyncSession, data: dict) -> Page:
    from app.shared.sanitize import sanitize_html

    slug = data.get("slug") or make_slug(data["title"])
    if await db.scalar(select(Page).where(Page.slug == slug)):
        raise ConflictError("Já existe uma página com esse slug.")
    p = Page(
        slug=slug,
        title=data["title"],
        body=sanitize_html(data.get("body", "")),
        is_published=data.get("is_published", True),
        seo_title=data.get("seo_title"),
        seo_description=data.get("seo_description"),
        updated_at=datetime.now(UTC),
    )
    db.add(p)
    await db.flush()
    return p


async def update_page(db: AsyncSession, page_id: str, data: dict) -> Page:
    from app.shared.sanitize import sanitize_html

    p = await db.get(Page, uuid.UUID(page_id))
    if not p:
        raise NotFoundError("Página não encontrada.")
    if data.get("body") is not None:
        data["body"] = sanitize_html(data["body"])
    for k in ("title", "body", "is_published", "seo_title", "seo_description", "slug"):
        if k in data and data[k] is not None:
            setattr(p, k, data[k])
    p.updated_at = datetime.now(UTC)
    return p


async def delete_page(db: AsyncSession, page_id: str) -> None:
    p = await db.get(Page, uuid.UUID(page_id))
    if p:
        await db.delete(p)
