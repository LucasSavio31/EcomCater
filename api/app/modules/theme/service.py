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
    "variation_bg_color", "variation_text_color", "variation_border_color",
    "header_bg_color", "header_text_color", "header_max_width_px",
    "footer_bg_color", "footer_text_color",
    "font_family", "free_shipping_threshold_cents", "whatsapp_number",
    "top_bar_message", "top_bar_enabled", "top_bar_carousel",
    "top_bar_message_2", "top_bar_message_3",
    "top_bar_bg_color", "top_bar_text_color",
    "hero_enabled", "hero_mode", "hero_autoplay_seconds",
    "footer_seals_enabled", "footer_seals_json",
    "cart_redirect_after_add",
    "checkout_email_first", "checkout_container_width_px", "checkout_items_layout",
    "checkout_show_coupon", "checkout_allow_qty_change", "checkout_footer_note",
    "checkout_bg_color", "checkout_header_bg_color", "checkout_header_text_color",
    "checkout_button_color", "checkout_button_text_color", "checkout_accent_color",
    "checkout_footer_bg_color", "checkout_footer_text_color",
    "checkout_animated_card", "checkout_show_review", "checkout_review_position",
    "checkout_orderbump_enabled", "checkout_orderbump_product_id",
    "checkout_orderbump_product_ids",
    "filter_size_enabled", "filter_price_enabled", "filter_category_enabled",
    "filter_color_enabled", "filter_material_enabled",
    "mini_cart_enabled",
    "newsletter_enabled", "newsletter_title", "newsletter_subtitle",
    "newsletter_bg_color", "newsletter_text_color",
    "newsletter_button_color", "newsletter_button_text_color",
    "discount_badge_enabled",
    "button_radius_px",
    "pdp_qty_selector_enabled", "wishlist_enabled",
    "card_hover_zoom_enabled", "card_buy_button_enabled", "card_buy_button_label",
    "cookie_consent_enabled", "cookie_consent_text",
    "email_header_bg_color", "email_header_text_color",
    "email_body_bg_color", "email_text_color",
    "email_button_color", "email_button_text_color", "email_footer_text",
    "lead_popup_enabled", "lead_capture_enabled",
    "lead_popup_title", "lead_popup_subtitle", "lead_popup_coupon_code",
    "lead_popup_bg_color", "lead_popup_text_color",
    "lead_popup_button_color", "lead_popup_button_text_color",
}

_BOOL_FIELDS = {
    "top_bar_enabled", "top_bar_carousel",
    "hero_enabled", "footer_seals_enabled", "cart_redirect_after_add",
    "mini_cart_enabled",
    "checkout_email_first", "checkout_show_coupon", "checkout_allow_qty_change",
    "checkout_animated_card", "checkout_show_review", "checkout_orderbump_enabled",
    "filter_size_enabled", "filter_price_enabled", "filter_category_enabled",
    "filter_color_enabled", "filter_material_enabled",
    "newsletter_enabled", "discount_badge_enabled",
    "cookie_consent_enabled",
    "lead_popup_enabled", "lead_capture_enabled",
    "pdp_qty_selector_enabled", "wishlist_enabled",
    "card_hover_zoom_enabled", "card_buy_button_enabled",
}


_DEFAULT_SEALS = {
    "payment": {
        "title": "Formas de Pagamento",
        "text": "",
        "badges": ["Pix", "Boleto", "Visa", "Mastercard", "Amex", "Elo", "Hipercard"],
    },
    "shipping": {"title": "Formas de Entrega", "text": "", "badges": ["Correios"]},
    "security": {
        "title": "Loja Segura",
        "text": "Site 100% seguro, com criptografia e certificado SSL.",
        "badges": ["SSL"],
    },
}


def _seals_out(row: ThemeSettings) -> dict:
    stored = row.footer_seals_json or {}
    result: dict = {}
    for col, default in _DEFAULT_SEALS.items():
        block = stored.get(col) if isinstance(stored.get(col), dict) else {}
        images = block.get("images") if isinstance(block.get("images"), list) else []
        images = [str(k) for k in images if k][:3]
        # com imagens enviadas os badges de texto default são descartados
        has_images = len(images) > 0
        result[col] = {
            "title": block.get("title") or default["title"],
            "text": block.get("text") if block.get("text") is not None else default["text"],
            "badges": block["badges"]
            if isinstance(block.get("badges"), list)
            else ([] if has_images else default["badges"]),
            "images": images,
            "image_urls": [storage.url(k) for k in images],
        }
    return result


def theme_out(row: ThemeSettings) -> dict:
    fields = {f: getattr(row, f) for f in _THEME_FIELDS}
    fields["footer_seals_json"] = _seals_out(row)
    return {
        **fields,
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
        if k not in _THEME_FIELDS:
            continue
        if v is None and k not in _BOOL_FIELDS:
            continue
        if k in _COLOR_FIELDS and not _HEX_RE.match(str(v)):
            raise ValidationError(f"Cor inválida em '{k}': use formato hexadecimal (#RRGGBB).")
        if k == "header_max_width_px":
            v = max(640, min(2560, int(v)))
        if k == "checkout_container_width_px":
            v = max(900, min(1600, int(v)))
        if k == "checkout_items_layout":
            v = "simple" if str(v) == "simple" else "with_thumb"
        if k == "checkout_review_position":
            v = "top" if str(v) == "top" else "side"
        if k == "checkout_orderbump_product_id":
            v = str(v).strip() or None
        if k == "lead_popup_coupon_code":
            v = str(v).strip().upper() or None
        if k == "checkout_orderbump_product_ids":
            v = [str(x).strip() for x in v if str(x).strip()][:20] if isinstance(v, list) else []
        if k == "hero_mode":
            v = "static" if str(v) == "static" else "carousel"
        if k == "hero_autoplay_seconds":
            v = max(0, min(30, int(v)))
        if k in _BOOL_FIELDS:
            v = bool(v)
        if k == "footer_seals_json":
            v = _clean_seals(v)
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


_SEAL_COLUMNS = ("payment", "shipping", "security")


def _clean_seals(raw: object) -> dict:
    """Normaliza {payment|shipping|security: {title, text?, badges:[str], images:[key]}}."""
    src = raw if isinstance(raw, dict) else {}
    out: dict = {}
    for col in _SEAL_COLUMNS:
        block = src.get(col) if isinstance(src.get(col), dict) else {}
        badges = block.get("badges")
        badges = [str(b).strip() for b in badges if str(b).strip()][:20] if isinstance(badges, list) else []
        images = block.get("images")
        images = [str(k).strip() for k in images if str(k).strip()][:3] if isinstance(images, list) else []
        out[col] = {
            "title": str(block.get("title") or "").strip()[:60],
            "text": str(block.get("text") or "").strip()[:240],
            "badges": badges,
            "images": images,
        }
    return out


async def set_seal_image(
    db: AsyncSession, column: str, index: int, raw: bytes, filename: str
) -> ThemeSettings:
    if column not in _SEAL_COLUMNS:
        raise ValidationError("Coluna de selo inválida.")
    if index not in (0, 1, 2):
        raise ValidationError("Posição de selo inválida (0 a 2).")
    row = await get_theme(db)
    seals = _clean_seals(row.footer_seals_json)
    processed = process_image(raw, filename, prefix="theme/seals")
    images = list(seals[column]["images"])
    if index < len(images):
        images[index] = processed.medium_key
    else:
        images.append(processed.medium_key)
    seals[column]["images"] = images[:3]
    row.footer_seals_json = seals  # reatribui p/ o SQLAlchemy detectar a mudança
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return row


async def remove_seal_image(db: AsyncSession, column: str, index: int) -> ThemeSettings:
    if column not in _SEAL_COLUMNS:
        raise ValidationError("Coluna de selo inválida.")
    row = await get_theme(db)
    seals = _clean_seals(row.footer_seals_json)
    images = list(seals[column]["images"])
    if 0 <= index < len(images):
        images.pop(index)
    seals[column]["images"] = images
    row.footer_seals_json = seals
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
