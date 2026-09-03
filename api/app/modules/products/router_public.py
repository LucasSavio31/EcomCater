"""Rotas públicas do módulo `products` (catálogo da loja)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import NS_CATALOG, NS_PRODUCT, cached_json
from app.core.database import get_db
from app.core.deps import get_current_customer
from app.core.ratelimit import rate_limit
from app.modules.customers.models import User
from app.modules.products import service
from app.modules.products.schemas import ProductDetail, ReviewIn

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentCustomer = Annotated[User, Depends(get_current_customer)]


@router.get("")
async def list_products(
    db: DbDep,
    category: str | None = None,
    price_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, ge=0),
    size: list[str] | None = Query(None),
    material: list[str] | None = Query(None),
    color: list[str] | None = Query(None),
    option_value: list[str] | None = Query(None),
    in_stock: bool | None = None,
    sort: str = "relevancia",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
) -> dict:
    key = {
        "category": category, "price_min": price_min, "price_max": price_max,
        "option_value": sorted(option_value or []), "size": sorted(size or []),
        "material": sorted(material or []), "color": sorted(color or []),
        "in_stock": in_stock, "sort": sort, "page": page, "page_size": page_size,
    }
    return await cached_json(
        NS_CATALOG, ("products:list", key), 60,
        lambda: service.list_products(
            db,
            category=category,
            price_min=price_min,
            price_max=price_max,
            option_values=option_value or [],
            sizes=size or [],
            materials=material or [],
            colors=color or [],
            in_stock=in_stock,
            sort=sort,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/featured")
async def featured(db: DbDep, limit: int = Query(12, ge=1, le=40)) -> list[dict]:
    return await cached_json(
        NS_CATALOG, ("products:featured", limit), 120,
        lambda: service.featured(db, limit),
    )


@router.get("/home-sections")
async def home_sections(db: DbDep) -> dict:
    """Blocos da home (Mais buscados / Tênis / Feminino) sorteados de forma
    determinística por hora — a semente é o carimbo AAAAMMDDHH (UTC), então a
    ordem troca sozinha a cada virada de hora. Cache expira junto com a hora."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    bucket = now.strftime("%Y%m%d%H")
    ttl = max(60, 3600 - (now.minute * 60 + now.second))
    return await cached_json(
        NS_CATALOG, ("products:home-sections", bucket), ttl,
        lambda: service.home_sections(db, seed=int(bucket)),
    )


@router.get("/by-ids")
async def by_ids(
    db: DbDep,
    ids: str = Query("", description="ids separados por vírgula"),
) -> list[dict]:
    parsed = [s.strip() for s in ids.split(",") if s.strip()]
    return await service.by_ids(db, parsed)


@router.get("/search")
async def search(
    db: DbDep,
    q: str = Query(min_length=1),
    limit: int = Query(8, ge=1, le=20),
) -> list[dict]:
    return await cached_json(
        NS_CATALOG, ("products:search", q.strip().lower(), limit), 45,
        lambda: service.search(db, q, limit),
    )


@router.get("/{slug}", response_model=ProductDetail)
async def get_product(slug: str, db: DbDep) -> dict:
    return await cached_json(
        NS_PRODUCT, ("products:detail", slug), 120,
        lambda: service.get_detail_by_slug(db, slug),
    )


@router.post("/{slug}/reviews", status_code=201)
async def create_review(
    slug: str,
    body: ReviewIn,
    db: DbDep,
    customer: CurrentCustomer,
    _rl: Annotated[None, Depends(rate_limit("5/minute", scope="review"))],
) -> dict:
    """Só clientes logados avaliam. A avaliação entra na fila de moderação."""
    product = await service.get_detail_by_slug(db, slug)
    review = await service.add_review(
        db,
        product["id"],
        {
            **body.model_dump(),
            "author_name": customer.full_name or (customer.email or "Cliente").split("@")[0],
            "user_id": str(customer.id),
        },
    )
    return {"id": str(review.id), "status": review.status}
