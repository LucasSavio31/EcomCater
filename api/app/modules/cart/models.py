"""Modelos do módulo `cart` — carrinho persistente (cliente logado ou convidado)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin


class Cart(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "carts"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL")
    )
    shipping_zip: Mapped[str | None] = mapped_column(String(8))
    selected_shipping_json: Mapped[dict | None] = mapped_column(JSONB)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[CartItem]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "variant_id", name="one_line_per_variant"),)

    cart_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE")
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_cents: Mapped[int] = mapped_column(Integer)  # snapshot na adição

    cart: Mapped[Cart] = relationship(back_populates="items")
