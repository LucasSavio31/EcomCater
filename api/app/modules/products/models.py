"""Modelos do módulo `products`: produto, variações/SKU, opções, imagens,
especificações, relacionados e avaliações."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

PRODUCT_STATUS = ("draft", "active", "archived")
REVIEW_STATUS = ("pending", "approved", "rejected")


class Product(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_products_status_featured", "status", "is_featured"),
    )

    name: Mapped[str] = mapped_column(String(240))
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True)
    sku_root: Mapped[str | None] = mapped_column(String(60), unique=True)
    short_description: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(120))
    # Fornecedor — uso interno (não aparece na loja). Base para separar PDFs/etiquetas.
    supplier: Mapped[str | None] = mapped_column(String(160), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(12), default="draft")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    compare_at_price_cents: Mapped[int | None] = mapped_column(Integer)
    pix_discount_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    installments_max: Mapped[int | None] = mapped_column(Integer)

    weight_grams: Mapped[int] = mapped_column(Integer, default=300)
    length_mm: Mapped[int] = mapped_column(Integer, default=100)
    width_mm: Mapped[int] = mapped_column(Integer, default=100)
    height_mm: Mapped[int] = mapped_column(Integer, default=50)

    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    seo_title: Mapped[str | None] = mapped_column(String(200))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product", cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    option_types: Mapped[list[VariantOptionType]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    specs: Mapped[list[ProductSpec]] = relationship(
        back_populates="product", cascade="all, delete-orphan",
        order_by="ProductSpec.position",
    )
    reviews: Mapped[list[ProductReview]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductCategory(Base):
    """N:N adicional além da categoria principal."""

    __tablename__ = "product_categories"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class VariantOptionType(UUIDPKMixin, Base):
    """Eixo de variação de um produto (ex.: 'Numeração', 'Cor')."""

    __tablename__ = "variant_option_types"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    is_size: Mapped[bool] = mapped_column(Boolean, default=False)  # eixo dos atalhos "compre por tamanho"
    is_color: Mapped[bool] = mapped_column(Boolean, default=False)  # eixo renderizado como miniaturas na PDP
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="option_types")
    values: Mapped[list[VariantOptionValue]] = relationship(
        back_populates="option_type", cascade="all, delete-orphan",
        order_by="VariantOptionValue.position",
    )


class VariantOptionValue(UUIDPKMixin, Base):
    __tablename__ = "variant_option_values"

    option_type_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("variant_option_types.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Miniatura da cor na PDP — aponta para uma imagem já cadastrada do produto.
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_images.id", ondelete="SET NULL")
    )

    option_type: Mapped[VariantOptionType] = relationship(back_populates="values")
    image: Mapped[ProductImage | None] = relationship("ProductImage", foreign_keys=[image_id])


class ProductVariant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    price_cents: Mapped[int | None] = mapped_column(Integer)  # null => herda do produto
    compare_at_price_cents: Mapped[int | None] = mapped_column(Integer)
    stock_qty: Mapped[int | None] = mapped_column(Integer, default=0)  # null => estoque ilimitado
    weight_grams: Mapped[int | None] = mapped_column(Integer)
    barcode: Mapped[str | None] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="variants")
    option_values: Mapped[list[VariantOptionValue]] = relationship(
        secondary="product_variant_options"
    )


class ProductVariantOption(Base):
    __tablename__ = "product_variant_options"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True
    )
    option_value_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("variant_option_values.id", ondelete="CASCADE"),
        primary_key=True,
    )


class ProductImage(UUIDPKMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    alt: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    original_filename: Mapped[str | None] = mapped_column(String(260))
    original_width: Mapped[int | None] = mapped_column(Integer)
    original_height: Mapped[int | None] = mapped_column(Integer)
    thumb_key: Mapped[str] = mapped_column(String(300))
    medium_key: Mapped[str] = mapped_column(String(300))
    zoom_key: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped[Product] = relationship(back_populates="images")


class ProductSpec(UUIDPKMixin, Base):
    __tablename__ = "product_specs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    group: Mapped[str | None] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(String(400))
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="specs")


class ProductRelated(Base):
    """N:N 'quem viu também gostou'."""

    __tablename__ = "product_related"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    related_product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


class ProductReview(UUIDPKMixin, Base):
    __tablename__ = "product_reviews"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    author_name: Mapped[str] = mapped_column(String(160))
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped[Product] = relationship(back_populates="reviews")

    __table_args__ = (UniqueConstraint("product_id", "user_id", name="one_review_per_user"),)
