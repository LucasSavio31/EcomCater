"""DTOs do módulo `categories`."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parent_id: str | None = None
    description: str | None = None
    position: int = 0
    is_active: bool = True
    seo_title: str | None = None
    seo_description: str | None = None


class CategoryCreateIn(CategoryBase):
    pass


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    parent_id: str | None = None
    description: str | None = None
    position: int | None = None
    is_active: bool | None = None
    seo_title: str | None = None
    seo_description: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    path: str
    parent_id: str | None
    description: str | None
    image_url: str | None
    position: int
    is_active: bool
    seo_title: str | None
    seo_description: str | None

    model_config = {"from_attributes": True}


class CategoryNode(BaseModel):
    id: str
    name: str
    slug: str
    path: str
    position: int
    is_active: bool
    product_count: int = 0
    children: list[CategoryNode] = []


class CategoryReorderItem(BaseModel):
    id: str
    position: int
    parent_id: str | None = None


class CategoryReorderIn(BaseModel):
    items: list[CategoryReorderItem]
