"""Regra de negócio do módulo `products` (catálogo)."""
from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy import update as sa_update
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
from app.shared.search import like_pattern_unaccent
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


def _looks_uuid(v: str) -> bool:
    try:
        uuid.UUID(str(v))
        return True
    except ValueError:
        return False


def _discount_pct(price: int, compare_at: int | None) -> int | None:
    if compare_at and compare_at > price > 0:
        return round((compare_at - price) / compare_at * 100)
    return None


def variant_price(product: Product, variant: ProductVariant) -> int:
    return variant.price_cents if variant.price_cents is not None else product.price_cents


def _min_variant_price(product: Product) -> int:
    prices = [variant_price(product, v) for v in product.variants if v.is_active]
    return min(prices) if prices else product.price_cents


def _variant_in_stock(v: ProductVariant) -> bool:
    return v.is_active and (v.stock_qty is None or v.stock_qty > 0)


def _in_stock(product: Product) -> bool:
    if not product.variants:
        return True
    return any(_variant_in_stock(v) for v in product.variants)


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
        # identidade comercial p/ analytics/feed do Merchant Center (item_group_id)
        "sku_root": product.sku_root,
        "brand": product.brand,
        "price_cents": price,
        "compare_at_price_cents": product.compare_at_price_cents,
        "discount_pct": _discount_pct(price, product.compare_at_price_cents),
        "pix_discount_pct": float(product.pix_discount_pct) if product.pix_discount_pct else None,
        "installments_max": product.installments_max,
        "in_stock": _in_stock(product),
        "is_featured": product.is_featured,
        "primary_image_url": storage.url(imgs[0].medium_key) if imgs else None,
        "hover_image_url": storage.url(imgs[1].medium_key) if len(imgs) > 1 else None,
        "rating_avg": float(product.rating_avg or 0),
        "rating_count": product.rating_count,
        "status": product.status,
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
        "in_stock": _variant_in_stock(v),
        "weight_grams": v.weight_grams or product.weight_grams,
        "is_active": v.is_active,
        "position": v.position,
    }


async def _breadcrumb(db: AsyncSession, category: Category | None) -> list[dict]:
    # a raiz ("Início") é adicionada pelo front — aqui só a trilha de categorias
    crumbs: list[dict] = []
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
        selectinload(Product.option_types)
        .selectinload(VariantOptionType.values)
        .selectinload(VariantOptionValue.image),
        selectinload(Product.specs),
        selectinload(Product.reviews),
    )


async def _color_siblings(
    db: AsyncSession, product: Product, *, include_unpublished: bool = False
) -> list[dict]:
    """Produtos irmãos de cor (mesmo color_group_id), incluindo o atual, ordenados
    por nome. Cada item traz a imagem principal para a miniatura da PDP."""
    if not product.color_group_id:
        return []
    stmt = select(Product).where(Product.color_group_id == product.color_group_id)
    if not include_unpublished:
        stmt = stmt.where(Product.status == "active")
    rows = list(await db.scalars(stmt.options(selectinload(Product.images))))
    rows.sort(key=lambda p: (p.color_name or p.name or "").lower())
    out: list[dict] = []
    for p in rows:
        imgs = sorted(p.images, key=lambda i: (not i.is_primary, i.position))
        out.append(
            {
                "id": str(p.id),
                "slug": p.slug,
                "name": p.name,
                "color_name": p.color_name or p.name,
                "image_url": storage.url(imgs[0].thumb_key) if imgs else None,
                "is_current": p.id == product.id,
            }
        )
    return out


async def get_detail_by_slug(db: AsyncSession, slug: str, *, include_unpublished: bool = False) -> dict:
    stmt = _detail_loader(select(Product).where(Product.slug == slug))
    product = await db.scalar(stmt)
    if not product or (not include_unpublished and product.status != "active"):
        raise NotFoundError("Produto não encontrado.")

    category = await db.get(Category, product.category_id) if product.category_id else None
    extra_category_ids = [
        str(cid)
        for cid in await db.scalars(
            select(ProductCategory.category_id).where(ProductCategory.product_id == product.id)
        )
    ]
    size_chart = None
    if product.size_chart_id:
        from app.modules.size_charts.models import SizeChart
        from app.modules.size_charts.service import out as _sc_out

        sc = await db.get(SizeChart, product.size_chart_id)
        size_chart = _sc_out(sc) if sc else None
    price = _min_variant_price(product)
    color_siblings = await _color_siblings(db, product, include_unpublished=include_unpublished)

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
    if not related and product.category_id:
        # sem relacionados explícitos: completa com produtos da mesma categoria
        fallback = await db.scalars(
            _detail_loader(
                select(Product)
                .where(
                    Product.category_id == product.category_id,
                    Product.id != product.id,
                    Product.status == "active",
                )
                .order_by(Product.is_featured.desc(), Product.published_at.desc().nullslast())
                .limit(8)
            )
        )
        related = [list_item(p) for p in fallback]

    def _value_out(v: VariantOptionValue) -> dict:
        img = v.image
        return {
            "id": str(v.id),
            "value": v.value,
            "position": v.position,
            "slug": make_slug(v.value) or str(v.id),
            "image_id": str(v.image_id) if v.image_id else None,
            "swatch_thumb_url": storage.url(img.thumb_key) if img else None,
            "swatch_medium_url": storage.url(img.medium_key) if img else None,
        }

    option_types = [
        {
            "id": str(ot.id),
            "name": ot.name,
            "is_size": ot.is_size,
            "is_color": ot.is_color,
            "position": ot.position,
            "values": [_value_out(v) for v in sorted(ot.values, key=lambda x: x.position)],
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
        "color_name": product.color_name,
        "color_siblings": color_siblings,
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
        "size_chart": size_chart,
        **({"size_chart_id": str(product.size_chart_id) if product.size_chart_id else None}
           if include_unpublished else {}),
        # fornecedor + vínculos de categoria: só no contexto admin (nunca na loja)
        **({"supplier": product.supplier} if include_unpublished else {}),
        **({
            "category_id": str(product.category_id) if product.category_id else None,
            "extra_category_ids": extra_category_ids,
        } if include_unpublished else {}),
    }


async def list_products(
    db: AsyncSession,
    *,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    option_values: list[str] | None = None,
    sizes: list[str] | None = None,
    materials: list[str] | None = None,
    colors: list[str] | None = None,
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
        ref = category.strip("/")
        # match por `path` (identificador canônico) vence o match por `slug`
        # quando o mesmo slug existe em mais de um nível da árvore.
        cat = await db.scalar(
            select(Category)
            .where(or_(Category.path == ref, Category.slug == ref))
            .order_by((Category.path == ref).desc())
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

    # o filtro de preço NÃO entra nos facets — o range de preço mostrado tem que
    # ser sempre o da categoria inteira (senão o slider "encolhe" a cada aplicação)
    price_conds: list[Any] = []
    if price_min is not None:
        price_conds.append(Product.price_cents >= price_min)
    if price_max is not None:
        price_conds.append(Product.price_cents <= price_max)

    if option_values:
        ov_ids = [_uuid(v) for v in option_values if _looks_uuid(v)]
        if ov_ids:
            conds.append(
                Product.id.in_(
                    select(ProductVariant.product_id)
                    .join(ProductVariant.option_values)
                    .where(VariantOptionValue.id.in_(ov_ids))
                )
            )

    def _axis_cond(is_size: bool | None, name_ilike: str | None, values: list[str]):
        q = (
            select(ProductVariant.product_id)
            .join(ProductVariant.option_values)
            .join(VariantOptionType, VariantOptionType.id == VariantOptionValue.option_type_id)
            .where(func.lower(VariantOptionValue.value).in_([v.lower() for v in values]))
        )
        if is_size is not None:
            q = q.where(VariantOptionType.is_size.is_(is_size))
        if name_ilike:
            q = q.where(func.lower(VariantOptionType.name) == name_ilike.lower())
        return Product.id.in_(q)

    if sizes:
        conds.append(_axis_cond(True, None, sizes))
    if materials:
        conds.append(_axis_cond(None, "Material", materials))
    if colors:
        conds.append(func.lower(Product.color_name).in_([c.lower() for c in colors]))

    all_conds = conds + price_conds
    base = select(Product).where(and_(*all_conds)) if all_conds else select(Product)
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

    # facets sem o filtro de preço (range de preço = o da categoria toda)
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

    def _axis_facet(is_size: bool | None, name_eq: str | None):
        q = (
            select(VariantOptionValue.value, func.count(func.distinct(ProductVariant.product_id)))
            .select_from(VariantOptionValue)
            .join(VariantOptionType, VariantOptionType.id == VariantOptionValue.option_type_id)
            .join(ProductVariantOption, ProductVariantOption.option_value_id == VariantOptionValue.id)
            .join(ProductVariant, ProductVariant.id == ProductVariantOption.variant_id)
            .where(ProductVariant.product_id.in_(product_ids))
            .group_by(VariantOptionValue.value, VariantOptionValue.position)
            .order_by(VariantOptionValue.position)
        )
        if is_size is not None:
            q = q.where(VariantOptionType.is_size.is_(is_size))
        if name_eq:
            q = q.where(func.lower(VariantOptionType.name) == name_eq.lower())
        return q

    size_rows = await db.execute(_axis_facet(True, None))
    sizes = [{"value": v, "count": int(n or 0)} for v, n in size_rows.all()]

    material_rows = await db.execute(_axis_facet(None, "Material"))
    materials = [{"value": v, "count": int(n or 0)} for v, n in material_rows.all()]

    color_rows = await db.execute(
        select(Product.color_name, func.count(Product.id))
        .where(Product.id.in_(product_ids), Product.color_name.is_not(None))
        .group_by(Product.color_name)
        .order_by(Product.color_name)
    )
    colors = [{"value": v, "count": int(n or 0)} for v, n in color_rows.all() if v]

    return {
        "price": {"min": int(pmin or 0), "max": int(pmax or 0)},
        "sizes": sizes,
        "materials": materials,
        "colors": colors,
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


async def home_sections(db: AsyncSession, *, seed: int) -> dict:
    """Três blocos da home, embaralhados de forma determinística por `seed`
    (o router usa o carimbo ano-mês-dia-hora → tudo re-sorteia a cada hora):

    - `mais_buscados`: 12 itens de todo o catálogo ativo
    - `tenis`:          8 itens do tipo tênis
    - `feminino`:       4 itens da árvore Feminino

    Nunca repete o mesmo MODELO num bloco: produtos que são a mesma peça em
    cores diferentes compartilham `color_group_id` — só um deles entra (qual
    cor também re-sorteia por hora).
    """
    import random as _random
    import re as _re

    def _model_key(p: Product) -> object:
        # "TENIS 2085 CAFE" -> ("m", "2085"); assim 2085 masc e 2085 fem contam
        # como o mesmo modelo. Sem número no nome: cai no grupo de cor / id.
        m = _re.search(r"\b(\d{3,4})\b", p.name or "")
        return ("m", m.group(1)) if m else (p.color_group_id or p.id)

    rows = sorted(
        await db.scalars(
            select(Product)
            .where(Product.status == "active")
            .options(selectinload(Product.variants), selectinload(Product.images))
        ),
        key=lambda p: str(p.id),
    )
    by_id = {p.id: p for p in rows}

    tenis_ids = set(
        await db.scalars(
            select(Product.id)
            .where(
                Product.status == "active",
                or_(
                    like_pattern_unaccent(Product.name, "tenis%"),
                    Product.id.in_(
                        select(ProductCategory.product_id)
                        .join(Category, Category.id == ProductCategory.category_id)
                        .where(Category.slug == "tenis")
                    ),
                    Product.category_id.in_(
                        select(Category.id).where(Category.slug == "tenis")
                    ),
                ),
            )
        )
    )
    fem_ids = set(
        await db.scalars(
            select(Product.id).where(
                Product.status == "active",
                or_(
                    Product.category_id.in_(
                        select(Category.id).where(
                            or_(Category.path == "feminino", Category.path.like("feminino/%"))
                        )
                    ),
                    Product.id.in_(
                        select(ProductCategory.product_id)
                        .join(Category, Category.id == ProductCategory.category_id)
                        .where(
                            or_(Category.path == "feminino", Category.path.like("feminino/%"))
                        )
                    ),
                ),
            )
        )
    )

    def _sample(pool_ids: set[uuid.UUID], n: int, *, dedupe_model: bool) -> list[dict]:
        rng = _random.Random(seed + n)  # bloco distinto → ordem distinta
        ids = sorted((i for i in pool_ids if i in by_id), key=str)
        if dedupe_model:
            # 1 representante por modelo; a cor escolhida re-sorteia por hora
            groups: dict[object, list[uuid.UUID]] = {}
            for pid in ids:
                groups.setdefault(_model_key(by_id[pid]), []).append(pid)
            ids = [g[rng.randrange(len(g))] if len(g) > 1 else g[0] for g in groups.values()]
        rng.shuffle(ids)
        return [list_item(by_id[i]) for i in ids[:n]]

    return {
        # "Mais buscados": nunca repete modelo. "Tênis"/"Feminino": podem repetir
        # cor do mesmo modelo pra completar a contagem — só a ordem re-sorteia.
        "mais_buscados": _sample({p.id for p in rows}, 12, dedupe_model=True),
        "tenis": _sample(set(tenis_ids), 8, dedupe_model=False),
        "feminino": _sample(set(fem_ids), 4, dedupe_model=False),
    }


async def by_ids(db: AsyncSession, ids: list[str], limit: int = 100) -> list[dict]:
    """Produtos ativos por lista de ids (favoritos). Preserva a ordem recebida."""
    clean = [i for i in dict.fromkeys(ids) if i][:limit]
    if not clean:
        return []
    rows = await db.scalars(
        select(Product)
        .where(Product.status == "active", Product.id.in_(clean))
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    order = {pid: n for n, pid in enumerate(clean)}
    items = sorted(rows, key=lambda p: order.get(str(p.id), len(order)))
    return [list_item(p) for p in items]


async def search(db: AsyncSession, q: str, limit: int = 8) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    # casa singular/plural simples ("bota" <-> "botas") sem depender de stemmer
    like = f"%{q}%"
    like_sing = f"%{q.rstrip('s')}%" if q.lower().endswith("s") else f"%{q}%"
    like_plur = f"%{q}s%" if not q.lower().endswith("s") else f"%{q}%"

    sim = func.similarity(Product.name, q)
    # categorias (e seus ancestrais) cujo nome bate → traz os produtos delas
    cat_ids_stmt = select(Category.id).where(
        Category.is_active.is_(True),
        or_(
            like_pattern_unaccent(Category.name, like),
            like_pattern_unaccent(Category.name, like_sing),
            like_pattern_unaccent(Category.name, like_plur),
            func.similarity(Category.name, q) > 0.2,
        ),
    )

    prod_rows = await db.scalars(
        select(Product)
        .where(Product.status == "active")
        .where(
            or_(
                like_pattern_unaccent(Product.name, like),
                like_pattern_unaccent(Product.brand, like),
                sim > 0.15,
                Product.category_id.in_(cat_ids_stmt),
                Product.id.in_(
                    select(ProductCategory.product_id).where(
                        ProductCategory.category_id.in_(cat_ids_stmt)
                    )
                ),
            )
        )
        .options(selectinload(Product.variants), selectinload(Product.images))
        .order_by(sim.desc(), Product.is_featured.desc(), Product.published_at.desc().nullslast())
        .limit(limit)
    )
    results: list[dict] = []
    for p in prod_rows:
        item = list_item(p)
        results.append(
            {
                **item,  # payload completo p/ o card padrão (desconto, PIX, etc.)
                "type": "product",
                "url": f"/produto/{p.slug}",
                # compat com o painel de busca (usa `image_url`)
                "image_url": item["primary_image_url"],
            }
        )

    cat_rows = await db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .where(
            or_(
                like_pattern_unaccent(Category.name, like),
                like_pattern_unaccent(Category.name, like_sing),
                like_pattern_unaccent(Category.name, like_plur),
                func.similarity(Category.name, q) > 0.2,
            )
        )
        # topo primeiro (path sem "/") p/ o dedupe por nome escolher a categoria "chapa"
        .order_by(func.length(Category.path) - func.length(func.replace(Category.path, "/", "")))
        .limit(12)
    )
    seen: set[str] = set()
    cats_out: list[dict] = []
    for c in cat_rows:
        key = c.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        cats_out.append(
            {"type": "category", "id": str(c.id), "name": c.name, "slug": c.slug,
             "url": f"/categoria/{c.path}", "price_cents": None, "image_url": None}
        )
        if len(cats_out) >= 4:
            break
    return results + cats_out


# --------------------------------------------------------------------- CRUD admin
async def create(db: AsyncSession, data: dict) -> Product:
    from app.shared.sanitize import sanitize_html

    if data.get("description"):
        data["description"] = sanitize_html(data["description"])
    slug = await _unique_slug(db, data["name"])
    extra = data.pop("extra_category_ids", []) or []
    for k in ("category_id", "size_chart_id"):
        if k in data:
            data[k] = _uuid(data[k]) if data[k] else None
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


async def _cleanup_color_group(db: AsyncSession, group_id: uuid.UUID | None) -> None:
    """Se o grupo de cor ficou com menos de 2 membros, dissolve-o."""
    if not group_id:
        return
    ids = list(await db.scalars(select(Product.id).where(Product.color_group_id == group_id)))
    if len(ids) < 2:
        await db.execute(
            sa_update(Product).where(Product.color_group_id == group_id).values(color_group_id=None)
        )


async def set_color_group(
    db: AsyncSession, product_id: str, *, color_name: str | None, sibling_ids: list[str]
) -> Product:
    """Define o rótulo de cor do produto e liga/desliga os produtos irmãos
    (mesma peça em outra cor). Todos os membros passam a compartilhar o
    `color_group_id`."""
    p = await get_admin(db, product_id)
    p.color_name = (color_name or "").strip() or None

    members = {p.id}
    for s in sibling_ids or []:
        try:
            members.add(_uuid(s))
        except ValidationError:
            continue
    old_gid = p.color_group_id

    if len(members) <= 1:
        p.color_group_id = None
        await db.flush()
        await _cleanup_color_group(db, old_gid)
        return await get_admin(db, product_id)

    existing = list(await db.scalars(select(Product).where(Product.id.in_(members))))
    if len(existing) != len(members):
        raise ValidationError("Um dos produtos irmãos não foi encontrado.")
    gid = next((m.color_group_id for m in existing if m.color_group_id), None) or uuid.uuid4()

    await db.execute(
        sa_update(Product).where(Product.id.in_(members)).values(color_group_id=gid)
    )
    if old_gid and old_gid != gid:
        await db.execute(
            sa_update(Product)
            .where(Product.color_group_id == old_gid, Product.id.notin_(members))
            .values(color_group_id=None)
        )
        await _cleanup_color_group(db, old_gid)
    await db.flush()
    return await get_admin(db, product_id)


_PRODUCT_COPY_FIELDS = (
    "short_description", "description", "brand", "supplier", "category_id",
    "price_cents", "compare_at_price_cents", "pix_discount_pct", "installments_max",
    "weight_grams", "length_mm", "width_mm", "height_mm",
    "seo_title", "seo_description",
)


def _copy_image_files(thumb: str, medium: str, zoom: str) -> tuple[str, str, str]:
    """Copia os 3 arquivos de uma imagem para uma nova pasta. Retorna as novas keys."""
    folder = f"products/{uuid.uuid4().hex}"
    out: list[str] = []
    for src, name in ((thumb, "thumb"), (medium, "medium"), (zoom, "zoom")):
        new_key = f"{folder}/{name}.webp"
        try:
            storage.save(new_key, storage.read(src), "image/webp")
        except Exception:  # noqa: BLE001 - arquivo sumiu; segue sem essa imagem
            return "", "", ""
        out.append(new_key)
    return out[0], out[1], out[2]


async def duplicate(db: AsyncSession, product_id: str) -> Product:
    """Clona um produto inteiro: dados, tipos/valores de variação, matriz de
    variações (SKUs novos), imagens (arquivos copiados) e especificações.
    O clone nasce como rascunho e sem destaque."""
    from datetime import UTC, datetime

    from app.modules.products.models import ProductVariantOption

    src = await get_admin(db, product_id)

    new = Product(
        name=f"{src.name} (cópia)",
        slug=await _unique_slug(db, f"{src.name} copia"),
        status="draft",
        is_featured=False,
        rating_avg=0,
        rating_count=0,
        published_at=None,
    )
    if src.sku_root:
        base = f"{src.sku_root}-COPY"
        cand, i = base, 2
        while await db.scalar(select(Product.id).where(Product.sku_root == cand)):
            cand, i = f"{base}{i}", i + 1
        new.sku_root = cand
    for f in _PRODUCT_COPY_FIELDS:
        setattr(new, f, getattr(src, f))
    db.add(new)
    await db.flush()

    # tipos + valores de opção
    value_map: dict[uuid.UUID, uuid.UUID] = {}
    for ot in sorted(src.option_types, key=lambda x: x.position):
        row = VariantOptionType(
            product_id=new.id, name=ot.name, is_size=ot.is_size,
            is_color=ot.is_color, position=ot.position,
        )
        db.add(row)
        await db.flush()
        for v in sorted(ot.values, key=lambda x: x.position):
            nv = VariantOptionValue(option_type_id=row.id, value=v.value, position=v.position)
            db.add(nv)
            await db.flush()
            value_map[v.id] = nv.id

    # imagens (copia arquivos) + mapa p/ corrigir referências
    image_map: dict[uuid.UUID, uuid.UUID] = {}
    for img in sorted(src.images, key=lambda i: (not i.is_primary, i.position)):
        t, m, z = _copy_image_files(img.thumb_key, img.medium_key, img.zoom_key)
        if not t:
            continue
        ni = ProductImage(
            product_id=new.id, alt=img.alt, position=img.position, is_primary=img.is_primary,
            original_filename=img.original_filename, original_width=img.original_width,
            original_height=img.original_height, thumb_key=t, medium_key=m, zoom_key=z,
            created_at=datetime.now(UTC),
        )
        db.add(ni)
        await db.flush()
        image_map[img.id] = ni.id

    # variações (SKUs novos) + vínculo de opções
    for var in sorted(src.variants, key=lambda x: x.position):
        base = f"{var.sku}-COPY"
        sku, i = base, 2
        while await db.scalar(select(ProductVariant.id).where(ProductVariant.sku == sku)):
            sku, i = f"{base}{i}", i + 1
        nvar = ProductVariant(
            product_id=new.id, sku=sku, price_cents=var.price_cents,
            compare_at_price_cents=var.compare_at_price_cents, stock_qty=var.stock_qty,
            weight_grams=var.weight_grams, barcode=None, is_active=var.is_active,
            position=var.position,
        )
        db.add(nvar)
        await db.flush()
        for ov in var.option_values:
            if ov.id in value_map:
                db.add(ProductVariantOption(variant_id=nvar.id, option_value_id=value_map[ov.id]))
        # imagens amarradas a esta variação
        for img in src.images:
            if img.variant_id == var.id and img.id in image_map:
                clone_img = await db.get(ProductImage, image_map[img.id])
                if clone_img:
                    clone_img.variant_id = nvar.id

    # miniatura de cor por valor
    for ot in src.option_types:
        for v in ot.values:
            if v.image_id and v.id in value_map and v.image_id in image_map:
                nv = await db.get(VariantOptionValue, value_map[v.id])
                if nv:
                    nv.image_id = image_map[v.image_id]

    # especificações
    for sp in sorted(src.specs, key=lambda s: s.position):
        db.add(ProductSpec(
            product_id=new.id, group=sp.group, label=sp.label, value=sp.value, position=sp.position,
        ))

    # categorias extras
    for pc in await db.scalars(select(ProductCategory).where(ProductCategory.product_id == src.id)):
        db.add(ProductCategory(product_id=new.id, category_id=pc.category_id))

    await db.flush()
    return await get_admin(db, str(new.id))


async def update(db: AsyncSession, product_id: str, data: dict) -> Product:
    from datetime import UTC, datetime

    from app.shared.sanitize import sanitize_html

    if data.get("description"):
        data["description"] = sanitize_html(data["description"])
    product = await get_admin(db, product_id)
    if "name" in data and data["name"] and data["name"] != product.name:
        product.name = data["name"]
        product.slug = await _unique_slug(db, data["name"], exclude=product.id)
    related = data.pop("related_product_ids", None)
    extra = data.pop("extra_category_ids", None)
    # size_chart_id / category_id: aceitam null explícito para DESVINCULAR
    for k in ("category_id", "size_chart_id"):
        if k in data:
            product_val = _uuid(data[k]) if data[k] else None
            setattr(product, k, product_val)
            data.pop(k)
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
    await db.flush()
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

    user_id = _uuid(data["user_id"]) if data.get("user_id") else None
    if user_id:
        existing = await db.scalar(
            select(ProductReview).where(
                ProductReview.product_id == product.id, ProductReview.user_id == user_id
            )
        )
        if existing:
            existing.rating = data["rating"]
            existing.title = data.get("title")
            existing.body = data.get("body")
            existing.status = "pending"
            existing.created_at = datetime.now(UTC)
            await db.flush()
            return existing

    review = ProductReview(
        product_id=product.id,
        user_id=user_id,
        author_name=data.get("author_name") or "Cliente",
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


async def list_all_reviews(
    db: AsyncSession, *, status: str | None = None, page: int = 1, page_size: int = 30
) -> dict:
    """Todas as avaliações da loja, para o menu de moderação."""
    stmt = select(ProductReview).options(selectinload(ProductReview.product))
    if status:
        stmt = stmt.where(ProductReview.status == status)
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = await db.scalars(
        stmt.order_by(ProductReview.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    items = [
        {
            "id": str(r.id),
            "product_id": str(r.product_id),
            "product_name": r.product.name if r.product else "—",
            "product_slug": r.product.slug if r.product else None,
            "author_name": r.author_name,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
