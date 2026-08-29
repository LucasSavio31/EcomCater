"""Regra de negócio do módulo `categories` — árvore, slug/path, reorder."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.categories.models import Category
from app.modules.products.models import Product
from app.shared.slugify import make_slug
from app.shared.storage import storage


def _uuid(v: str | uuid.UUID | None) -> uuid.UUID | None:
    if v is None or isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(v)
    except ValueError as exc:
        raise ValidationError("id inválido") from exc


async def _slug_exists(db: AsyncSession, parent_id: uuid.UUID | None, slug: str, exclude: uuid.UUID | None) -> bool:
    stmt = select(Category.id).where(Category.slug == slug)
    stmt = stmt.where(Category.parent_id == parent_id) if parent_id else stmt.where(Category.parent_id.is_(None))
    if exclude:
        stmt = stmt.where(Category.id != exclude)
    return (await db.scalar(stmt)) is not None


async def _unique_slug(db, parent_id, name, exclude=None) -> str:
    base = make_slug(name) or "categoria"
    cand, i = base, 2
    while await _slug_exists(db, parent_id, cand, exclude):
        cand = f"{base}-{i}"
        i += 1
    return cand


async def _compute_path(db: AsyncSession, parent_id: uuid.UUID | None, slug: str) -> str:
    if not parent_id:
        return slug
    parent = await db.get(Category, parent_id)
    if not parent:
        raise NotFoundError("Categoria pai não encontrada.")
    return f"{parent.path}/{slug}"


async def _repath_subtree(db: AsyncSession, category: Category) -> None:
    """Recalcula `path` do nó e de toda a descendência (após rename/move)."""
    children = list(await db.scalars(select(Category).where(Category.parent_id == category.id)))
    for child in children:
        child.path = f"{category.path}/{child.slug}"
        await _repath_subtree(db, child)


def _url(key: str | None) -> str | None:
    return storage.url(key) if key else None


async def list_all(db: AsyncSession) -> list[Category]:
    return list(await db.scalars(select(Category).order_by(Category.path, Category.position)))


async def get_by_id(db: AsyncSession, category_id: str) -> Category:
    cat = await db.get(Category, _uuid(category_id))
    if not cat:
        raise NotFoundError("Categoria não encontrada.")
    return cat


async def get_by_slug_or_path(db: AsyncSession, ref: str) -> Category:
    ref = ref.strip("/")
    stmt = select(Category).where((Category.path == ref) | (Category.slug == ref))
    cat = await db.scalar(stmt.limit(1))
    if not cat:
        raise NotFoundError("Categoria não encontrada.")
    return cat


async def _product_counts(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.status == "active")
        .group_by(Product.category_id)
    )
    return {cid: n for cid, n in rows.all() if cid is not None}


async def build_tree(db: AsyncSession, *, only_active: bool = True) -> list[dict]:
    cats = await list_all(db)
    counts = await _product_counts(db)
    by_parent: dict[uuid.UUID | None, list[Category]] = {}
    for c in cats:
        if only_active and not c.is_active:
            continue
        by_parent.setdefault(c.parent_id, []).append(c)

    def node(c: Category) -> dict:
        kids = sorted(by_parent.get(c.id, []), key=lambda x: (x.position, x.name))
        child_nodes = [node(k) for k in kids]
        return {
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "path": c.path,
            "position": c.position,
            "is_active": c.is_active,
            "product_count": counts.get(c.id, 0) + sum(cn["product_count"] for cn in child_nodes),
            "children": child_nodes,
        }

    roots = sorted(by_parent.get(None, []), key=lambda x: (x.position, x.name))
    return [node(r) for r in roots]


async def create(db: AsyncSession, data: dict) -> Category:
    parent_id = _uuid(data.get("parent_id"))
    slug = await _unique_slug(db, parent_id, data["name"])
    path = await _compute_path(db, parent_id, slug)
    cat = Category(
        name=data["name"],
        slug=slug,
        path=path,
        parent_id=parent_id,
        description=data.get("description"),
        position=data.get("position", 0),
        is_active=data.get("is_active", True),
        seo_title=data.get("seo_title"),
        seo_description=data.get("seo_description"),
    )
    db.add(cat)
    await db.flush()
    return cat


async def update(db: AsyncSession, category_id: str, data: dict) -> Category:
    cat = await get_by_id(db, category_id)
    new_parent = _uuid(data["parent_id"]) if "parent_id" in data else cat.parent_id
    if new_parent == cat.id:
        raise ValidationError("Uma categoria não pode ser pai dela mesma.")
    if new_parent and await _is_descendant(db, ancestor=cat.id, node=new_parent):
        raise ValidationError("Não é possível mover para dentro da própria subárvore.")

    rename = "name" in data and data["name"] and data["name"] != cat.name
    moved = new_parent != cat.parent_id

    for f in ("name", "description", "position", "is_active", "seo_title", "seo_description"):
        if f in data and data[f] is not None:
            setattr(cat, f, data[f])

    if rename or moved:
        cat.parent_id = new_parent
        cat.slug = await _unique_slug(db, new_parent, cat.name, exclude=cat.id)
        cat.path = await _compute_path(db, new_parent, cat.slug)
        await db.flush()
        await _repath_subtree(db, cat)
    return cat


async def _is_descendant(db: AsyncSession, *, ancestor: uuid.UUID, node: uuid.UUID) -> bool:
    current = await db.get(Category, node)
    while current and current.parent_id:
        if current.parent_id == ancestor:
            return True
        current = await db.get(Category, current.parent_id)
    return False


async def delete(db: AsyncSession, category_id: str) -> None:
    cat = await get_by_id(db, category_id)
    has_children = await db.scalar(select(Category.id).where(Category.parent_id == cat.id).limit(1))
    if has_children:
        raise ConflictError("Remova ou mova as subcategorias antes de excluir.")
    has_products = await db.scalar(
        select(Product.id).where(Product.category_id == cat.id).limit(1)
    )
    if has_products:
        raise ConflictError("Há produtos nesta categoria. Reatribua-os antes de excluir.")
    await db.delete(cat)


async def reorder(db: AsyncSession, items: Iterable[dict]) -> None:
    for it in items:
        cat = await db.get(Category, _uuid(it["id"]))
        if not cat:
            continue
        cat.position = it["position"]
        if "parent_id" not in it:
            continue
        new_parent = _uuid(it["parent_id"])
        if new_parent == cat.parent_id:
            continue
        if new_parent and (
            new_parent == cat.id
            or await _is_descendant(db, ancestor=cat.id, node=new_parent)
        ):
            raise ValidationError("Reorder inválido: ciclo na árvore de categorias.")
        cat.parent_id = new_parent
        cat.slug = await _unique_slug(db, new_parent, cat.name, exclude=cat.id)
        cat.path = await _compute_path(db, new_parent, cat.slug)
        await db.flush()
        await _repath_subtree(db, cat)


async def set_image(db: AsyncSession, category_id: str, raw: bytes, filename: str) -> Category:
    from app.shared.images import process_image

    cat = await get_by_id(db, category_id)
    processed = process_image(raw, filename, prefix="categories")
    cat.image_key = processed.medium_key
    return cat


def to_out(cat: Category) -> dict:
    return {
        "id": str(cat.id),
        "name": cat.name,
        "slug": cat.slug,
        "path": cat.path,
        "parent_id": str(cat.parent_id) if cat.parent_id else None,
        "description": cat.description,
        "image_url": _url(cat.image_key),
        "position": cat.position,
        "is_active": cat.is_active,
        "seo_title": cat.seo_title,
        "seo_description": cat.seo_description,
    }
