"""Regra de negócio do módulo `products` (catálogo)."""
from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.categories.models import Category
from app.modules.products.models import (
    Product,
    ProductCategory,
    ProductImage,
    ProductRelated,
    ProductReview,
    ProductSpec,
    ProductVariant,
    VariantOptionType,
    VariantOptionValue,
)
from app.shared.slugify import make_slug
from app.shared.storage import storage

SORTS = {
    "relevancia": (Product.is_featured.desc(), Product.published_at.desc()),
    "menor-preco": (Product.price_cents.asc(),),
    "maior-preco": (Product.price_cents.desc(),),
    "lancamentos": (Product.published_at.desc().nullslast(),),
}


def _uuid(v: str | uuid.UUID | None) -> uuid.UUID | None:
    if v is None or isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


def _discount_pct(price: int, compare_at: int | None) -> int | None:
    if compare_at and compare_at > price > 0:
        return round((compare_at - price) / compare_at * 100)
    return None


def variant_price(product: Product, variant: ProductVariant) -> int:
    return variant.price_cents if variant.price_cents is not None else product.price_cents


def _min_variant_price(product: Product) -> int:
    prices = [variant_price(product, v) for v in product.variants if v.is_active]
    return min(prices) if prices else product.price_cents


def _in_stock(product: Product) -> bool:
    if not product.variants:
        return True
    return any(v.is_active and v.stock_qty > 0 for v in product.variants)


# --------------------------------------------------------------------- slug
async def _unique_slug(db: AsyncSession, name: str, exclude: uuid.UUID | None = None) -> str:
    base = make_slug(name) or "produto"
    cand, i = base, 2
    while True:
        stmt = select(Product.id).where(Product.slug == cand)
        if exclude:
            stmt = stmt.where(Product.id != exclude)
        if not await db.scalar(stmt):
            return cand
        cand = f"{base}-{i}"
        i += 1


# --------------------------------------------------------------------- serialização
def _img_out(img: ProductImage) -> dict:
    return {
        "id": str(img.id),
        "alt": img.alt,
        "position": img.position,
        "is_primary": img.is_primary,
        "variant_id": str(img.variant_id) if img.variant_id else None,
        "thumb_url": storage.url(img.thumb_key),
        "medium_url": storage.url(img.medium_key),
        "zoom_url": storage.url(img.zoom_key),
    }


def list_item(product: Product) -> dict:
    price = _min_variant_price(product)
    imgs = sorted(product.images, key=lambda i: (not i.is_primary, i.position))
    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "brand": product.brand,
        "price_cents": price,
        "compare_at_price_cents": product.compare_at_price_cents,
        "discount_pct": _discount_pct(price, product.compare_at_price_cents),
        "installments_max": product.installments_max,
        "in_stock": _in_stock(product),
        "is_featured": product.is_featured,
        "primary_image_url": storage.url(imgs[0].medium_key) if imgs else None,
        "hover_image_url": storage.url(imgs[1].medium_key) if len(imgs) > 1 else None,
        "rating_avg": float(product.rating_avg or 0),
        "rating_count": product.rating_count,
    }


def _variant_out(product: Product, v: ProductVariant) -> dict:
    labels = [ov.value for ov in v.option_values]
    return {
        "id": str(v.id),
        "sku": v.sku,
        "option_value_ids": [str(ov.id) for ov in v.option_values],
        "option_labels": labels,
        "price_cents": variant_price(product, v),
        "compare_at_price_cents": v.compare_at_price_cents or product.compare_at_price_cents,
        "stock_qty": v.stock_qty,
        "in_stock": v.is_active and v.stock_qty > 0,
        "weight_grams": v.weight_grams or product.weight_grams,
        "is_active": v.is_active,
        "position": v.position,
    }


async def _breadcrumb(db: AsyncSession, category: Category | None) -> list[dict]:
    crumbs: list[dict] = [{"name": "Home", "url": "/"}]
    chain: list[Category] = []
    current = category
    while current:
        chain.append(current)
        current = await db.get(Category, current.parent_id) if current.parent_id else None
    for c in reversed(chain):
        crumbs.append({"name": c.name, "url": f"/categoria/{c.path}"})
    return crumbs


# --------------------------------------------------------------------- consultas públicas
def _detail_loader(stmt: Select) -> Select:
    return stmt.options(
        selectinload(Product.variants).selectinload(ProductVariant.option_values),
        selectinload(Product.images),
        selectinload(Product.option_types).selectinload(VariantOptionType.values),
        selectinload(Product.specs),
        selectinload(Product.reviews),
    )


async def get_detail_by_slug(db: AsyncSession, slug: str, *, include_unpublished: bool = False) -> dict:
    stmt = _detail_loader(select(Product).where(Product.slug == slug))
    product = await db.scalar(stmt)
    if not product or (not include_unpublished and product.status != "active"):
        raise NotFoundError("Produto não encontrado.")

    category = await db.get(Category, product.category_id) if product.category_id else None
    price = _min_variant_price(product)

    related_ids = [
        r.related_product_id
        for r in sorted(
            await db.scalars(
                select(ProductRelated).where(ProductRelated.product_id == product.id)
            ),
            key=lambda r: r.position,
        )
    ]
    related: list[dict] = []
    if related_ids:
        rel = await db.scalars(
            _detail_loader(select(Product).where(Product.id.in_(related_ids), Product.status == "active"))
        )
        by_id = {p.id: p for p in rel}
        related = [list_item(by_id[i]) for i in related_ids if i in by_id]

    option_types = [
        {
            "id": str(ot.id),
            "name": ot.name,
            "is_size": ot.is_size,
            "position": ot.position,
            "values": [
                {"id": str(v.id), "value": v.value, "position": v.position}
                for v in sorted(ot.values, key=lambda x: x.position)
            ],
        }
        for ot in sorted(product.option_types, key=lambda x: x.position)
    ]

    reviews = [
        {
            "id": str(r.id),
            "author_name": r.author_name,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in product.reviews
        if r.status == "approved"
    ]

    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "sku_root": product.sku_root,
        "short_description": product.short_description,
        "description": product.description,
        "brand": product.brand,
        "category": {"id": str(category.id), "name": category.name, "slug": category.slug, "path": category.path}
        if category
        else None,
        "breadcrumb": await _breadcrumb(db, category),
        "status": product.status,
        "is_featured": product.is_featured,
        "price_cents": price,
        "compare_at_price_cents": product.compare_at_price_cents,
        "discount_pct": _discount_pct(price, product.compare_at_price_cents),
        "pix_discount_pct": float(product.pix_discount_pct) if product.pix_discount_pct else None,
        "installments_max": product.installments_max,
        "weight_grams": product.weight_grams,
        "dimensions_mm": {
            "length": product.length_mm,
            "width": product.width_mm,
            "height": product.height_mm,
        },
        "rating_avg": float(product.rating_avg or 0),
        "rating_count": product.rating_count,
        "seo_title": product.seo_title,
        "seo_description": product.seo_description,
        "option_types": option_types,
        "variants": [
            _variant_out(product, v)
            for v in sorted(product.variants, key=lambda x: x.position)
        ],
        "images": [_img_out(i) for i in sorted(product.images, key=lambda i: (not i.is_primary, i.position))],
        "specs": [
            {"id": str(s.id), "group": s.group, "label": s.label, "value": s.value, "position": s.position}
            for s in sorted(product.specs, key=lambda s: s.position)
        ],
        "related": related,
        "reviews": reviews,
    }


async def list_products(
    db: AsyncSession,
    *,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    option_values: list[str] | None = None,
    in_stock: bool | None = None,
    sort: str = "relevancia",
    page: int = 1,
    page_size: int = 24,
    only_active: bool = True,
) -> dict:
    conds: list[Any] = []
    if only_active:
        conds.append(Product.status == "active")

    if category:
        cat = await db.scalar(
            select(Category).where(
                or_(Category.path == category.strip("/"), Category.slug == category)
            )
        )
        if not cat:
            raise NotFoundError("Categoria não encontrada.")
        sub_ids = await _descendant_category_ids(db, cat.id)
        conds.append(
            or_(
                Product.category_id.in_(sub_ids),
                Product.id.in_(
                    select(ProductCategory.product_id).where(
                        ProductCategory.category_id.in_(sub_ids)
                    )
                ),
            )
        )

    if price_min is not None:
        conds.append(Product.price_cents >= price_min)
    if price_max is not None:
        conds.append(Product.price_cents <= price_max)

    if option_values:
        ov_ids = [_uuid(v) for v in option_values]
        conds.append(
            Product.id.in_(
                select(ProductVariant.product_id)
                .join(ProductVariant.option_values)
                .where(VariantOptionValue.id.in_(ov_ids))
            )
        )

    base = select(Product).where(and_(*conds)) if conds else select(Product)
    total = int(await db.scalar(select(func.count()).select_from(base.subquery())) or 0)

    order = SORTS.get(sort, SORTS["relevancia"])
    stmt = (
        base.options(selectinload(Product.variants), selectinload(Product.images))
        .order_by(*order)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = list(await db.scalars(stmt))
    items = [list_item(p) for p in rows]
    if in_stock is not None:
        items = [i for i in items if i["in_stock"] == in_stock]

    facets = await _facets(db, and_(*conds) if conds else None)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if page_size else 0,
        "facets": facets,
    }


async def _descendant_category_ids(db: AsyncSession, root: uuid.UUID) -> list[uuid.UUID]:
    root_cat = await db.get(Category, root)
    if not root_cat:
        return [root]
    rows = await db.scalars(
        select(Category.id).where(
            or_(Category.id == root, Category.path.like(f"{root_cat.path}/%"))
        )
    )
    return list(rows)


async def _facets(db: AsyncSession, where) -> dict:
    base = select(Product) if where is None else select(Product).where(where)
    product_ids = select(base.subquery().c.id)

    price_row = await db.execute(
        select(func.min(Product.price_cents), func.max(Product.price_cents)).where(
            Product.id.in_(product_ids)
        )
    )
    pmin, pmax = price_row.first() or (0, 0)

    from app.modules.products.models import ProductVariantOption

    size_rows = await db.execute(
        select(VariantOptionValue.value, func.count(func.distinct(ProductVariant.product_id)))
        .select_from(VariantOptionValue)
        .join(VariantOptionType, VariantOptionType.id == VariantOptionValue.option_type_id)
        .join(ProductVariantOption, ProductVariantOption.option_value_id == VariantOptionValue.id)
        .join(ProductVariant, ProductVariant.id == ProductVariantOption.variant_id)
        .where(VariantOptionType.is_size.is_(True))
        .where(ProductVariant.product_id.in_(product_ids))
        .group_by(VariantOptionValue.value, VariantOptionValue.position)
        .order_by(VariantOptionValue.position)
    )
    sizes = [{"value": v, "count": int(n or 0)} for v, n in size_rows.all()]

    return {
        "price": {"min": int(pmin or 0), "max": int(pmax or 0)},
        "sizes": sizes,
    }


async def featured(db: AsyncSession, limit: int = 12) -> list[dict]:
    rows = await db.scalars(
        select(Product)
        .where(Product.status == "active", Product.is_featured.is_(True))
        .options(selectinload(Product.variants), selectinload(Product.images))
        .order_by(Product.published_at.desc().nullslast())
        .limit(limit)
    )
    return [list_item(p) for p in rows]


async def search(db: AsyncSession, q: str, limit: int = 8) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    sim = func.similarity(Product.name, q)
    prod_rows = await db.scalars(
        select(Product)
        .where(Product.status == "active")
        .where(or_(Product.name.ilike(f"%{q}%"), sim > 0.1))
        .options(selectinload(Product.variants), selectinload(Product.images))
        .order_by(sim.desc(), Product.is_featured.desc())
        .limit(limit)
    )
    results: list[dict] = []
    for p in prod_rows:
        item = list_item(p)
        results.append(
            {
                "type": "product",
                "id": item["id"],
                "name": p.name,
                "slug": p.slug,
                "url": f"/produto/{p.slug}",
                "price_cents": item["price_cents"],
                "image_url": item["primary_image_url"],
            }
        )

    cat_rows = await db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .where(or_(Category.name.ilike(f"%{q}%"), func.similarity(Category.name, q) > 0.1))
        .limit(4)
    )
    for c in cat_rows:
        results.append(
            {"type": "category", "id": str(c.id), "name": c.name, "slug": c.slug,
             "url": f"/categoria/{c.path}", "price_cents": None, "image_url": None}
        )
    return results


# --------------------------------------------------------------------- CRUD admin
async def create(db: AsyncSession, data: dict) -> Product:
    slug = await _unique_slug(db, data["name"])
    extra = data.pop("extra_category_ids", []) or []
    product = Product(slug=slug, **{k: v for k, v in data.items() if k != "extra_category_ids"})
    if product.status == "active" and product.published_at is None:
        from datetime import UTC, datetime

        product.published_at = datetime.now(UTC)
    db.add(product)
    await db.flush()
    for cid in extra:
        db.add(ProductCategory(product_id=product.id, category_id=_uuid(cid)))
    return product


async def get_admin(db: AsyncSession, product_id: str) -> Product:
    product = await db.scalar(_detail_loader(select(Product).where(Product.id == _uuid(product_id))))
    if not product:
        raise NotFoundError("Produto não encontrado.")
    return product


async def update(db: AsyncSession, product_id: str, data: dict) -> Product:
    from datetime import UTC, datetime

    product = await get_admin(db, product_id)
    if "name" in data and data["name"] and data["name"] != product.name:
        product.name = data["name"]
        product.slug = await _unique_slug(db, data["name"], exclude=product.id)
    related = data.pop("related_product_ids", None)
    extra = data.pop("extra_category_ids", None)
    for k, v in data.items():
        if k in ("name", "slug"):
            continue
        if v is not None:
            setattr(product, k, v)
    if product.status == "active" and product.published_at is None:
        product.published_at = datetime.now(UTC)

    if extra is not None:
        for pc in await db.scalars(select(ProductCategory).where(ProductCategory.product_id == product.id)):
            await db.delete(pc)
        for cid in extra:
            db.add(ProductCategory(product_id=product.id, category_id=_uuid(cid)))

    if related is not None:
        for pr in await db.scalars(select(ProductRelated).where(ProductRelated.product_id == product.id)):
            await db.delete(pr)
        for pos, rid in enumerate(related):
            if _uuid(rid) != product.id:
                db.add(ProductRelated(product_id=product.id, related_product_id=_uuid(rid), position=pos))
    return product


async def set_status(db: AsyncSession, product_id: str, status: str) -> Product:
    if status not in ("draft", "active", "archived"):
        raise ValidationError(f"Status inválido: {status}")
    product = await get_admin(db, product_id)
    product.status = status
    if status == "active" and product.published_at is None:
        from datetime import UTC, datetime

        product.published_at = datetime.now(UTC)
    return product


async def delete(db: AsyncSession, product_id: str) -> None:
    product = await get_admin(db, product_id)
    from app.modules.orders.models import OrderItem

    used = await db.scalar(select(OrderItem.id).where(OrderItem.product_id == product.id).limit(1))
    if used:
        raise ConflictError(
            "Produto já usado em pedidos — arquive em vez de excluir (dados de pedido são imutáveis)."
        )
    await db.delete(product)


# --------------------------------------------------------------------- imagens
async def add_image(
    db: AsyncSession, product_id: str, raw: bytes, filename: str, *, variant_id: str | None = None, alt: str | None = None
) -> ProductImage:
    from app.shared.images import process_image

    product = await get_admin(db, product_id)
    processed = process_image(raw, filename, prefix="products")
    count = len(product.images)
    img = ProductImage(
        product_id=product.id,
        variant_id=_uuid(variant_id),
        alt=alt or product.name,
        position=count,
        is_primary=(count == 0),
        original_filename=processed.original_filename,
        original_width=processed.original_width,
        original_height=processed.original_height,
        thumb_key=processed.thumb_key,
        medium_key=processed.medium_key,
        zoom_key=processed.zoom_key,
    )
    db.add(img)
    await db.flush()
    return img


async def delete_image(db: AsyncSession, product_id: str, image_id: str) -> None:
    img = await db.get(ProductImage, _uuid(image_id))
    if not img or str(img.product_id) != str(_uuid(product_id)):
        raise NotFoundError("Imagem não encontrada.")
    for key in (img.thumb_key, img.medium_key, img.zoom_key):
        storage.delete(key)
    await db.delete(img)


async def reorder_images(db: AsyncSession, product_id: str, ordered_ids: list[str], primary_id: str | None = None) -> None:
    product = await get_admin(db, product_id)
    pos = {str(i): n for n, i in enumerate(ordered_ids)}
    for img in product.images:
        if str(img.id) in pos:
            img.position = pos[str(img.id)]
        img.is_primary = str(img.id) == str(primary_id) if primary_id else img.position == 0


# --------------------------------------------------------------------- specs
async def replace_specs(db: AsyncSession, product_id: str, specs: list[dict]) -> Product:
    product = await get_admin(db, product_id)
    for s in list(product.specs):
        await db.delete(s)
    for pos, s in enumerate(specs):
        db.add(
            ProductSpec(
                product_id=product.id,
                group=s.get("group"),
                label=s["label"],
                value=s["value"],
                position=s.get("position", pos),
            )
        )
    await db.flush()
    return await get_admin(db, product_id)


# --------------------------------------------------------------------- reviews
async def add_review(db: AsyncSession, product_id: str, data: dict) -> ProductReview:
    from datetime import UTC, datetime

    product = await db.get(Product, _uuid(product_id))
    if not product:
        raise NotFoundError("Produto não encontrado.")
    review = ProductReview(
        product_id=product.id,
        author_name=data["author_name"],
        rating=data["rating"],
        title=data.get("title"),
        body=data.get("body"),
        status="pending",
        created_at=datetime.now(UTC),
    )
    db.add(review)
    await db.flush()
    return review


async def moderate_review(db: AsyncSession, review_id: str, status: str) -> ProductReview:
    if status not in ("approved", "rejected", "pending"):
        raise ValidationError("Status de review inválido.")
    review = await db.get(ProductReview, _uuid(review_id))
    if not review:
        raise NotFoundError("Avaliação não encontrada.")
    review.status = status
    await db.flush()
    await _recompute_rating(db, review.product_id)
    return review


async def _recompute_rating(db: AsyncSession, product_id: uuid.UUID) -> None:
    row = await db.execute(
        select(func.avg(ProductReview.rating), func.count(ProductReview.id)).where(
            ProductReview.product_id == product_id, ProductReview.status == "approved"
        )
    )
    avg, count = row.first() or (None, 0)
    product = await db.get(Product, product_id)
    if product:
        product.rating_avg = round(float(avg), 2) if avg else 0
        product.rating_count = int(count or 0)


async def list_reviews(db: AsyncSession, product_id: str, *, status: str | None = None) -> list[ProductReview]:
    stmt = select(ProductReview).where(ProductReview.product_id == _uuid(product_id))
    if status:
        stmt = stmt.where(ProductReview.status == status)
    return list(await db.scalars(stmt.order_by(ProductReview.created_at.desc())))
