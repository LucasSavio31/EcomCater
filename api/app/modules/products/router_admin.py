"""Rotas administrativas do módulo `products`."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_admin, require_role
from app.modules.admin.models import AdminUser
from app.modules.products import service, service_variants
from app.modules.products.models import Product
from app.modules.products.schemas import (
    ColorGroupIn,
    OptionTypeIn,
    OptionTypePatchIn,
    OptionValueAddIn,
    OptionValueUpdateIn,
    ProductCreateIn,
    ProductUpdateIn,
    ReviewModerateIn,
    SpecIn,
    VariantIn,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
EditorDep = Annotated[AdminUser, Depends(require_role("admin", "staff"))]


@router.get("")
async def list_products(
    db: DbDep,
    _: AdminDep,
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
) -> dict:
    stmt = select(Product).options(selectinload(Product.variants), selectinload(Product.images))
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if status_filter:
        stmt = stmt.where(Product.status == status_filter)
    from sqlalchemy import func

    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = await db.scalars(
        stmt.order_by(Product.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    )
    return {
        "items": [service.list_item(p) for p in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{product_id}", response_model=None)
async def get_product(product_id: str, db: DbDep, _: AdminDep) -> dict:
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreateIn, db: DbDep, _: EditorDep) -> dict:
    product = await service.create(db, body.model_dump())
    return {"id": str(product.id), "slug": product.slug}


@router.patch("/{product_id}")
async def update_product(product_id: str, body: ProductUpdateIn, db: DbDep, _: EditorDep) -> dict:
    product = await service.update(db, product_id, body.model_dump(exclude_unset=True))
    return {"id": str(product.id), "slug": product.slug, "status": product.status}


@router.post("/{product_id}/status")
async def set_status(product_id: str, db: DbDep, _: EditorDep, value: str = Query(...)) -> dict:
    product = await service.set_status(db, product_id, value)
    return {"id": str(product.id), "status": product.status}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete(db, product_id)


@router.post("/{product_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_product(product_id: str, db: DbDep, _: EditorDep) -> dict:
    product = await service.duplicate(db, product_id)
    return {"id": str(product.id), "slug": product.slug, "name": product.name}


@router.put("/{product_id}/color-group", response_model=None)
async def set_color_group(product_id: str, body: ColorGroupIn, db: DbDep, _: EditorDep) -> dict:
    await service.set_color_group(
        db, product_id, color_name=body.color_name, sibling_ids=body.sibling_ids
    )
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


# ------------------------------------------------------------------ eixos de opção
@router.put("/{product_id}/option-types")
async def set_option_types(
    product_id: str, body: list[OptionTypeIn], db: DbDep, _: EditorDep
) -> dict:
    await service_variants.replace_option_types(db, product_id, [o.model_dump() for o in body])
    return {"ok": True}


@router.patch("/{product_id}/option-types/{type_id}", response_model=None)
async def patch_option_type(
    product_id: str, type_id: str, body: OptionTypePatchIn, db: DbDep, _: EditorDep
) -> dict:
    await service_variants.patch_option_type(
        db, product_id, type_id, body.model_dump(exclude_unset=True)
    )
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


@router.post("/{product_id}/option-types/{type_id}/values", response_model=None, status_code=201)
async def add_option_value(
    product_id: str, type_id: str, body: OptionValueAddIn, db: DbDep, _: EditorDep
) -> dict:
    await service_variants.add_option_value(db, product_id, type_id, body.value)
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


@router.patch("/{product_id}/option-values/{value_id}", response_model=None)
async def update_option_value(
    product_id: str, value_id: str, body: OptionValueUpdateIn, db: DbDep, _: EditorDep
) -> dict:
    await service_variants.update_option_value(
        db, product_id, value_id, body.model_dump(exclude_unset=True)
    )
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


@router.delete("/{product_id}/option-values/{value_id}", response_model=None)
async def delete_option_value(
    product_id: str, value_id: str, db: DbDep, _: EditorDep
) -> dict:
    await service_variants.delete_option_value(db, product_id, value_id)
    return await service.get_detail_by_slug(
        db, (await service.get_admin(db, product_id)).slug, include_unpublished=True
    )


# ------------------------------------------------------------------ variações
@router.post("/{product_id}/variants", status_code=201)
async def create_variant(product_id: str, body: VariantIn, db: DbDep, _: EditorDep) -> dict:
    v = await service_variants.upsert_variant(db, product_id, body.model_dump())
    return {"id": str(v.id), "sku": v.sku}


@router.patch("/{product_id}/variants/{variant_id}")
async def update_variant(
    product_id: str, variant_id: str, body: VariantIn, db: DbDep, _: EditorDep
) -> dict:
    v = await service_variants.upsert_variant(db, product_id, body.model_dump(), variant_id)
    return {"id": str(v.id), "sku": v.sku}


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_variant(product_id: str, variant_id: str, db: DbDep, _: EditorDep) -> None:
    await service_variants.delete_variant(db, product_id, variant_id)


# ------------------------------------------------------------------ imagens
@router.post("/{product_id}/images", status_code=201)
async def add_image(
    product_id: str,
    db: DbDep,
    _: EditorDep,
    file: Annotated[UploadFile, File()],
    variant_id: Annotated[str | None, Form()] = None,
    alt: Annotated[str | None, Form()] = None,
) -> dict:
    raw = await file.read()
    img = await service.add_image(
        db, product_id, raw, file.filename or "produto.png", variant_id=variant_id, alt=alt
    )
    return {"id": str(img.id)}


@router.delete("/{product_id}/images/{image_id}", status_code=204)
async def delete_image(product_id: str, image_id: str, db: DbDep, _: EditorDep) -> None:
    await service.delete_image(db, product_id, image_id)


@router.post("/{product_id}/images/reorder", status_code=204)
async def reorder_images(
    product_id: str,
    db: DbDep,
    _: EditorDep,
    ordered_ids: list[str],
    primary_id: str | None = None,
) -> None:
    await service.reorder_images(db, product_id, ordered_ids, primary_id)


# ------------------------------------------------------------------ specs
@router.put("/{product_id}/specs")
async def replace_specs(product_id: str, body: list[SpecIn], db: DbDep, _: EditorDep) -> dict:
    await service.replace_specs(db, product_id, [s.model_dump() for s in body])
    return {"ok": True}


# ------------------------------------------------------------------ reviews
@router.get("/reviews/all", response_model=None)
async def all_reviews(
    db: DbDep,
    _: AdminDep,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    """Todas as avaliações da loja — menu de moderação."""
    return await service.list_all_reviews(db, status=status_filter, page=page, page_size=page_size)


@router.post("/reviews/{review_id}/moderate")
async def moderate_any_review(
    review_id: str, body: ReviewModerateIn, db: DbDep, _: EditorDep
) -> dict:
    r = await service.moderate_review(db, review_id, body.status)
    return {"id": str(r.id), "status": r.status}


@router.get("/{product_id}/reviews")
async def list_reviews(
    product_id: str, db: DbDep, _: AdminDep, status_filter: str | None = Query(None, alias="status")
) -> list[dict]:
    rows = await service.list_reviews(db, product_id, status=status_filter)
    return [
        {
            "id": str(r.id),
            "author_name": r.author_name,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/{product_id}/reviews/{review_id}/moderate")
async def moderate_review(
    product_id: str, review_id: str, body: ReviewModerateIn, db: DbDep, _: EditorDep
) -> dict:
    r = await service.moderate_review(db, review_id, body.status)
    return {"id": str(r.id), "status": r.status}
