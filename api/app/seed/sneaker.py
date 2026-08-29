"""Seed de um tênis aleatório para testes locais.

Uso:  python -m app.seed.sneaker
Cria (ou reaproveita) a categoria Calçados > Tênis, um produto ativo com eixo de
numeração 37–43, estoque, preço aleatório e 3 imagens WebP geradas.
"""
from __future__ import annotations

import asyncio
import io
import logging
import random
import uuid
from datetime import UTC, datetime

from PIL import Image, ImageDraw
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.categories.models import Category
from app.modules.products import service as product_service
from app.modules.products import service_variants
from app.modules.products.models import (
    Product,
    ProductImage,
    VariantOptionType,
    VariantOptionValue,
)
from app.shared.images import process_image
from app.shared.slugify import make_slug

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed.sneaker")

_BRANDS = ["Nordic Run", "Zephyr", "Caterpillar", "Volt", "Terra", "Kodiak", "Pace Lab"]
_LINES = ["Colorado", "Trailblazer", "Aero", "Storm", "Canyon", "Pulse", "Drift", "Summit"]
_COLORWAYS = ["Dark Shadow", "Bone White", "Total Black", "Sand", "Forest", "Steel Blue", "Rust"]
_SIZES = ["37", "38", "39", "40", "41", "42", "43"]
_PALETTE = ["#1f2937", "#111827", "#7c2d12", "#334155", "#1e3a8a", "#3f3f46"]


def _placeholder(text: str, color: str, size: int = 1200) -> bytes:
    img = Image.new("RGB", (size, size), color)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.08, size * 0.08, size * 0.92, size * 0.92], outline="white", width=8)
    d.ellipse([size * 0.2, size * 0.55, size * 0.8, size * 0.78], fill="white")
    d.text((size * 0.12, size * 0.12), text[:40], fill="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _ensure_category(db, name: str, parent: Category | None) -> Category:
    slug = make_slug(name)
    parent_id = parent.id if parent else None
    found = await db.scalar(
        select(Category).where(Category.slug == slug, Category.parent_id == parent_id)
    )
    if found:
        return found
    path = f"{parent.path}/{slug}" if parent else slug
    cat = Category(name=name, slug=slug, path=path, parent_id=parent_id, is_active=True)
    db.add(cat)
    await db.flush()
    return cat


async def run() -> None:
    async with SessionLocal() as db:
        calcados = await _ensure_category(db, "Calçados", None)
        tenis_cat = await _ensure_category(db, "Tênis", calcados)

        brand = random.choice(_BRANDS)
        name = f"Tênis {brand} {random.choice(_LINES)} {random.choice(_COLORWAYS)}"
        slug = make_slug(name)
        if await db.scalar(select(Product).where(Product.slug == slug)):
            name = f"{name} {random.randint(2, 99)}"
            slug = make_slug(name)

        price = random.randrange(24900, 89900, 1000) + 90  # ex.: 349,90
        compare_at = price + random.randrange(4000, 15000, 1000)
        color = random.choice(_PALETTE)

        product = await product_service.create(
            db,
            {
                "name": name,
                "sku_root": f"TEN-{random.randint(1000, 9999)}",
                "short_description": f"{name} — cabedal têxtil, solado de borracha e palmilha macia.",
                "description": (
                    f"<p><strong>{name}</strong> é um tênis casual para o dia a dia. "
                    "Cabedal respirável, forro acolchoado e solado com boa tração.</p>"
                    "<ul><li>Fechamento em cadarço</li><li>Solado de borracha</li>"
                    "<li>Palmilha removível</li></ul>"
                ),
                "brand": brand,
                "category_id": str(tenis_cat.id),
                "status": "active",
                "is_featured": True,
                "price_cents": price,
                "compare_at_price_cents": compare_at,
                "pix_discount_pct": 5,
                "installments_max": 10,
                "weight_grams": 850,
            },
        )
        product.published_at = datetime.now(UTC)
        await db.flush()

        product_id = str(product.id)
        sku_root = product.sku_root
        # eixo de numeração 37–43 + uma variação por número, com estoque
        await service_variants.replace_option_types(
            db,
            product_id,
            [{"name": "Numeração", "is_size": True, "values": [{"value": s} for s in _SIZES]}],
        )
        await db.flush()
        db.expunge_all()  # descarta o identity-map (coleções antigas ficariam vazias)

        values = list(
            await db.scalars(
                select(VariantOptionValue)
                .join(VariantOptionType, VariantOptionValue.option_type_id == VariantOptionType.id)
                .where(VariantOptionType.product_id == uuid.UUID(product_id))
                .order_by(VariantOptionValue.position)
            )
        )
        for k, ov in enumerate(values):
            await service_variants.upsert_variant(
                db,
                product_id,
                {
                    "sku": f"{sku_root}-{ov.value}",
                    "option_value_ids": [str(ov.id)],
                    "stock_qty": random.choice([0, 6, 12, 20]) if k else 15,
                    "position": k,
                },
            )
        product = await db.get(Product, uuid.UUID(product_id))

        for j in range(3):
            processed = process_image(
                _placeholder(f"{name} #{j + 1}", color), f"{slug}-{j}.png", prefix="products"
            )
            db.add(
                ProductImage(
                    product_id=product.id,
                    alt=f"{name} — foto {j + 1}",
                    position=j,
                    is_primary=(j == 0),
                    original_filename=processed.original_filename,
                    original_width=processed.original_width,
                    original_height=processed.original_height,
                    thumb_key=processed.thumb_key,
                    medium_key=processed.medium_key,
                    zoom_key=processed.zoom_key,
                )
            )

        await db.commit()
        logger.info(
            "tênis criado: %s | R$ %.2f | slug=/produto/%s | %d numerações",
            name,
            price / 100,
            slug,
            len(values),
        )


if __name__ == "__main__":
    asyncio.run(run())
