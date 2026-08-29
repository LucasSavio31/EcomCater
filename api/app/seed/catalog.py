"""Seed de catálogo para dev/testes — árvore de categorias + produtos com
variações e imagens geradas (exercita o pipeline WebP)."""
from __future__ import annotations

import io
import logging
from datetime import UTC, datetime

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories.models import Category
from app.modules.products import service as product_service
from app.modules.products import service_variants
from app.modules.products.models import Product
from app.shared.images import process_image
from app.shared.slugify import make_slug

logger = logging.getLogger("seed.catalog")

_COLORS = ["#1f2937", "#b91c1c", "#047857", "#7c3aed", "#d97706", "#0369a1"]

CATEGORIES = [
    ("Feminino", ["Vestidos", "Blusas", "Calçados"]),
    ("Masculino", ["Camisetas", "Calças", "Calçados"]),
    ("Acessórios", ["Bolsas", "Cintos"]),
]

SIZES = ["36", "38", "40", "42", "44"]


def _placeholder_png(text: str, color: str, size: int = 900) -> bytes:
    img = Image.new("RGB", (size, size), color)
    d = ImageDraw.Draw(img)
    d.rectangle([size * 0.1, size * 0.1, size * 0.9, size * 0.9], outline="white", width=6)
    d.text((size * 0.15, size * 0.45), text[:24], fill="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _ensure_category(db: AsyncSession, name: str, parent: Category | None) -> Category:
    parent_id = parent.id if parent else None
    slug = make_slug(name)
    existing = await db.scalar(
        select(Category).where(Category.slug == slug, Category.parent_id == parent_id)
    )
    if existing:
        return existing
    path = f"{parent.path}/{slug}" if parent else slug
    cat = Category(name=name, slug=slug, path=path, parent_id=parent_id, is_active=True)
    db.add(cat)
    await db.flush()
    return cat


async def run(db: AsyncSession, *, products_per_leaf: int = 3) -> None:
    if await db.scalar(select(Product).limit(1)):
        logger.info("catálogo já populado — pulando")
        return

    leaves: list[Category] = []
    for top_name, subs in CATEGORIES:
        top = await _ensure_category(db, top_name, None)
        for sub_name in subs:
            leaves.append(await _ensure_category(db, sub_name, top))

    n = 0
    for leaf in leaves:
        for i in range(products_per_leaf):
            n += 1
            name = f"{leaf.name} Modelo {i + 1}"
            color = _COLORS[n % len(_COLORS)]
            product = await product_service.create(
                db,
                {
                    "name": name,
                    "sku_root": f"SKU-{n:04d}",
                    "short_description": f"{name} — peça de demonstração.",
                    "description": f"<p>Descrição completa de {name}.</p>",
                    "brand": "Marca Demo",
                    "category_id": str(leaf.id),
                    "status": "active",
                    "is_featured": (n % 5 == 0),
                    "price_cents": 4990 + n * 700,
                    "compare_at_price_cents": (4990 + n * 700 + 3000) if n % 3 == 0 else None,
                    "pix_discount_pct": 5,
                    "installments_max": 6,
                    "weight_grams": 400,
                },
            )
            product.published_at = datetime.now(UTC)

            # eixo de tamanho + variações
            await service_variants.replace_option_types(
                db,
                str(product.id),
                [{"name": "Numeração", "is_size": True, "values": [{"value": s} for s in SIZES]}],
            )
            product = await service_variants._get_product(db, str(product.id))
            size_values = product.option_types[0].values
            for k, ov in enumerate(size_values):
                await service_variants.upsert_variant(
                    db,
                    str(product.id),
                    {
                        "sku": f"{product.sku_root}-{ov.value}",
                        "option_value_ids": [str(ov.id)],
                        "stock_qty": 0 if k == len(size_values) - 1 else 12,
                        "position": k,
                    },
                )

            # 2 imagens
            for j in range(2):
                processed = process_image(
                    _placeholder_png(f"{name} {j + 1}", color), f"{make_slug(name)}-{j}.png", prefix="products"
                )
                from app.modules.products.models import ProductImage

                db.add(
                    ProductImage(
                        product_id=product.id,
                        alt=name,
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
            await db.flush()

    await db.commit()
    logger.info("catálogo seed: %d produtos em %d subcategorias", n, len(leaves))
