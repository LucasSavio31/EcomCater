"""Regra de negócio do módulo `banners`."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.modules.banners.models import Banner
from app.shared.images import process_image
from app.shared.storage import storage


def _uuid(v: str | uuid.UUID) -> uuid.UUID:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


def _out(b: Banner) -> dict:
    desktop = storage.url(b.image_desktop_key) if b.image_desktop_key else None
    mobile = storage.url(b.image_mobile_key) if b.image_mobile_key else None
    return {
        "id": str(b.id),
        "slot": b.slot,
        "title": b.title,
        # `image_url` = desktop (compat); telas usam desktop/mobile explicitamente
        "image_url": desktop,
        "image_desktop_url": desktop,
        "image_mobile_url": mobile,
        "link_url": b.link_url,
        "alt": b.alt,
        "position": b.position,
        "starts_at": b.starts_at,
        "ends_at": b.ends_at,
        "is_active": b.is_active,
    }


async def list_public(db: AsyncSession, slot: str | None = None) -> list[dict]:
    now = datetime.now(UTC)
    stmt = select(Banner).where(
        Banner.is_active.is_(True),
        or_(Banner.starts_at.is_(None), Banner.starts_at <= now),
        or_(Banner.ends_at.is_(None), Banner.ends_at >= now),
    )
    if slot:
        stmt = stmt.where(Banner.slot == slot)
    rows = await db.scalars(stmt.order_by(Banner.slot, Banner.position))
    return [_out(b) for b in rows]


async def list_admin(db: AsyncSession) -> list[dict]:
    rows = await db.scalars(select(Banner).order_by(Banner.slot, Banner.position))
    return [_out(b) for b in rows]


async def create(db: AsyncSession, data: dict) -> Banner:
    b = Banner(**{k: v for k, v in data.items() if k in _FIELDS})
    db.add(b)
    await db.flush()
    return b


async def update(db: AsyncSession, banner_id: str, data: dict) -> Banner:
    b = await db.get(Banner, _uuid(banner_id))
    if not b:
        raise NotFoundError("Banner não encontrado.")
    for k, v in data.items():
        if k in _FIELDS and v is not None:
            setattr(b, k, v)
    return b


async def delete(db: AsyncSession, banner_id: str) -> None:
    b = await db.get(Banner, _uuid(banner_id))
    if not b:
        raise NotFoundError("Banner não encontrado.")
    for key in (b.image_desktop_key, b.image_mobile_key):
        if key:
            storage.delete(key)
    await db.delete(b)


def _is_animated_gif(raw: bytes) -> bool:
    try:
        import io

        from PIL import Image as _Img

        with _Img.open(io.BytesIO(raw)) as im:
            return getattr(im, "is_animated", False) and getattr(im, "n_frames", 1) > 1
    except Exception:  # noqa: BLE001
        return False


async def set_image(
    db: AsyncSession, banner_id: str, raw: bytes, filename: str,
    *, variant: str = "desktop", **_ignored,
) -> Banner:
    """Aceita qualquer formato de imagem. GIF animado é mantido como GIF
    (preserva a animação); os demais viram WebP pelo pipeline padrão.
    `variant` = "desktop" (padrão) ou "mobile" — a imagem mobile só aparece
    em telas pequenas e a desktop só em telas grandes."""
    b = await db.get(Banner, _uuid(banner_id))
    if not b:
        raise NotFoundError("Banner não encontrado.")
    field = "image_mobile_key" if variant == "mobile" else "image_desktop_key"

    old = getattr(b, field)
    if _is_animated_gif(raw):
        key = f"banners/{uuid.uuid4().hex}/banner.gif"
        storage.save(key, raw, "image/gif")
    else:
        processed = process_image(raw, filename, prefix="banners")
        key = processed.zoom_key
    setattr(b, field, key)
    if old and old != key:
        storage.delete(old)
    return b


async def clear_image(db: AsyncSession, banner_id: str, variant: str = "desktop") -> Banner:
    b = await db.get(Banner, _uuid(banner_id))
    if not b:
        raise NotFoundError("Banner não encontrado.")
    field = "image_mobile_key" if variant == "mobile" else "image_desktop_key"
    old = getattr(b, field)
    if old:
        storage.delete(old)
    setattr(b, field, None)
    return b


_FIELDS = {"slot", "title", "link_url", "alt", "position", "starts_at", "ends_at", "is_active"}
