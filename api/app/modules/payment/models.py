"""Modelos do módulo `payment` — cobranças e eventos de webhook (idempotência)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

PAYMENT_METHODS = ("credit_card", "pix", "boleto")
PAYMENT_STATES = ("pending", "authorized", "paid", "failed", "refunded", "chargeback")


class Payment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), default="appmax")
    method: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    installments: Mapped[int | None] = mapped_column(Integer)
    provider_charge_id: Mapped[str | None] = mapped_column(String(120), index=True)
    provider_payload_json: Mapped[dict | None] = mapped_column(JSONB)

    pix_qr_code: Mapped[str | None] = mapped_column(String(2000))
    pix_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    boleto_url: Mapped[str | None] = mapped_column(String(500))
    boleto_barcode: Mapped[str | None] = mapped_column(String(120))

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentWebhookEvent(UUIDPKMixin, Base):
    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="idempotency"),
    )

    provider: Mapped[str] = mapped_column(String(40))
    provider_event_id: Mapped[str] = mapped_column(String(120))
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
