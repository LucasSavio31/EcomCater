"""DTOs do módulo `products`."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ----------------------------------------------------------------- opções/variações
class OptionValueIn(BaseModel):
    value: str
    position: int = 0


class OptionTypeIn(BaseModel):
    name: str
    is_size: bool = False
    is_color: bool = False
    position: int = 0
    values: list[OptionValueIn] = []


class OptionTypePatchIn(BaseModel):
    name: str | None = None
    is_size: bool | None = None
    is_color: bool | None = None


class OptionValueAddIn(BaseModel):
    value: str


class ColorGroupIn(BaseModel):
    color_name: str | None = None
    sibling_ids: list[str] = []


class OptionValueUpdateIn(BaseModel):
    value: str | None = None
    image_id: str | None = None


class OptionValueOut(BaseModel):
    id: str
    value: str
    position: int
    slug: str | None = None
    image_id: str | None = None
    swatch_thumb_url: str | None = None
    swatch_medium_url: str | None = None


class OptionTypeOut(BaseModel):
    id: str
    name: str
    is_size: bool
    is_color: bool = False
    position: int
    values: list[OptionValueOut]


class VariantIn(BaseModel):
    sku: str
    option_value_ids: list[str] = []
    price_cents: int | None = None
    compare_at_price_cents: int | None = None
    stock_qty: int | None = 0  # None => estoque ilimitado
    weight_grams: int | None = None
    barcode: str | None = None
    is_active: bool = True
    position: int = 0


class VariantOut(BaseModel):
    id: str
    sku: str
    option_value_ids: list[str]
    option_labels: list[str]
    price_cents: int
    compare_at_price_cents: int | None
    stock_qty: int | None
    in_stock: bool
    weight_grams: int | None
    is_active: bool
    position: int


# ----------------------------------------------------------------- specs / imagens / reviews
class SpecIn(BaseModel):
    group: str | None = None
    label: str
    value: str
    position: int = 0


class SpecOut(SpecIn):
    id: str


class ImageOut(BaseModel):
    id: str
    alt: str | None
    position: int
    is_primary: bool
    variant_id: str | None
    thumb_url: str
    medium_url: str
    zoom_url: str


class ReviewIn(BaseModel):
    author_name: str = Field(min_length=2, max_length=160)
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    body: str | None = None


class ReviewOut(BaseModel):
    id: str
    author_name: str
    rating: int
    title: str | None
    body: str | None
    status: str
    created_at: str | None = None


class ReviewModerateIn(BaseModel):
    status: str  # approved | rejected | pending


# ----------------------------------------------------------------- produto
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    sku_root: str | None = None
    short_description: str | None = None
    description: str | None = None
    brand: str | None = None
    supplier: str | None = None
    category_id: str | None = None
    extra_category_ids: list[str] = []
    status: str = "draft"
    is_featured: bool = False
    price_cents: int = 0
    compare_at_price_cents: int | None = None
    pix_discount_pct: float | None = None
    installments_max: int | None = None
    weight_grams: int = 300
    length_mm: int = 100
    width_mm: int = 100
    height_mm: int = 50
    seo_title: str | None = None
    seo_description: str | None = None


class ProductCreateIn(ProductBase):
    pass


class ProductUpdateIn(BaseModel):
    name: str | None = None
    sku_root: str | None = None
    short_description: str | None = None
    description: str | None = None
    brand: str | None = None
    supplier: str | None = None
    category_id: str | None = None
    extra_category_ids: list[str] | None = None
    status: str | None = None
    is_featured: bool | None = None
    price_cents: int | None = None
    compare_at_price_cents: int | None = None
    pix_discount_pct: float | None = None
    installments_max: int | None = None
    weight_grams: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    related_product_ids: list[str] | None = None


class ProductListItem(BaseModel):
    id: str
    name: str
    slug: str
    brand: str | None
    price_cents: int
    compare_at_price_cents: int | None
    discount_pct: int | None
    installments_max: int | None
    in_stock: bool
    is_featured: bool
    primary_image_url: str | None
    hover_image_url: str | None
    rating_avg: float
    rating_count: int


class ProductDetail(BaseModel):
    id: str
    name: str
    slug: str
    sku_root: str | None
    short_description: str | None
    description: str | None
    brand: str | None
    category: dict | None
    breadcrumb: list[dict]
    status: str
    is_featured: bool
    price_cents: int
    compare_at_price_cents: int | None
    discount_pct: int | None
    pix_discount_pct: float | None
    installments_max: int | None
    weight_grams: int
    dimensions_mm: dict
    rating_avg: float
    rating_count: int
    seo_title: str | None
    seo_description: str | None
    color_name: str | None = None
    color_siblings: list[dict] = []
    option_types: list[OptionTypeOut]
    variants: list[VariantOut]
    images: list[ImageOut]
    specs: list[SpecOut]
    related: list[ProductListItem]
    reviews: list[ReviewOut]


class SearchResultItem(BaseModel):
    type: str  # product | category
    id: str
    name: str
    slug: str
    url: str
    price_cents: int | None = None
    image_url: str | None = None


class PagedProducts(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    page_size: int
    pages: int
    facets: dict
