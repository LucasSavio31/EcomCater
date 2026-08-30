"""Modelos do módulo `cart_recovery` — carrinhos abandonados + mensagens."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin


class RecoveryMessage(UUIDPKMixin, Base):
    __tablename__ = "recovery_messages"

    position: Mapped[int] = mapped_column(Integer, default=0)
    # minutos após a captura do e-mail no checkout
    delay_minutes: Mapped[int] = mapped_column(Integer, default=60)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AbandonedCart(UUIDPKMixin, Base):
    __tablename__ = "abandoned_carts"

    email: Mapped[str] = mapped_column(String(200), index=True)
    cart_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("carts.id", ondelete="SET NULL")
    )
    cart_token: Mapped[str] = mapped_column(String(64))
    total_cents: Mapped[int] = mapped_column(Integer, default=0)
    items_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
