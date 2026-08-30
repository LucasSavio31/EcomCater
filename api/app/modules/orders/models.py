"""Modelos do módulo `orders` — pedido, itens (snapshot imutável) e linha do tempo."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

ORDER_STATUS = (
    "pending_payment", "paid", "processing", "shipped", "delivered", "canceled", "refunded",
)
PAYMENT_STATUS = ("pending", "authorized", "paid", "failed", "refunded", "chargeback")
FULFILLMENT_STATUS = ("unfulfilled", "partial", "fulfilled")


class Order(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    email: Mapped[str] = mapped_column(String(200))
    cpf: Mapped[str | None] = mapped_column(String(11))

    status: Mapped[str] = mapped_column(String(20), default="pending_payment", index=True)
    payment_status: Mapped[str] = mapped_column(String(16), default="pending")
    fulfillment_status: Mapped[str] = mapped_column(String(16), default="unfulfilled")

    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    items_total_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    shipping_cents: Mapped[int] = mapped_column(Integer, default=0)
    grand_total_cents: Mapped[int] = mapped_column(Integer, default=0)

    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL")
    )
    coupon_code: Mapped[str | None] = mapped_column(String(60))

    shipping_method: Mapped[str | None] = mapped_column(String(120))
    shipping_service_json: Mapped[dict | None] = mapped_column(JSONB)
    shipping_address_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    billing_address_json: Mapped[dict | None] = mapped_column(JSONB)

    customer_note: Mapped[str | None] = mapped_column(Text)
    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    events: Mapped[list[OrderEvent]] = relationship(
        back_populates="order", cascade="all, delete-orphan",
        order_by="OrderEvent.created_at",
    )


class OrderItem(UUIDPKMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    sku: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(240))
    variant_label: Mapped[str | None] = mapped_column(String(160))
    # Variação estruturada editável pelo admin: {"cor": "...", "numero": "..."}
    variant_attrs: Mapped[dict | None] = mapped_column(JSONB)
    supplier: Mapped[str | None] = mapped_column(String(160))  # snapshot p/ PDF/etiqueta
    image_key: Mapped[str | None] = mapped_column(String(300))
    unit_price_cents: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    total_cents: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(UUIDPKMixin, Base):
    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(10), default="system")  # system|admin|customer
    actor_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="events")
