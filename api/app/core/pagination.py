"""Paginação por offset, padronizada para todas as listagens."""
from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 24


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


async def paginate(db: AsyncSession, stmt: Select, params: PageParams) -> tuple[list, int]:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    total = int(total or 0)
    rows = await db.execute(
        stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)
    )
    return list(rows.scalars().all()), total


def build_page(items: list, total: int, params: PageParams) -> dict:
    pages = (total + params.page_size - 1) // params.page_size if params.page_size else 0
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": pages,
    }
