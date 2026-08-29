"""Modelo do módulo `shipping` — espelho/auditoria de cotações (TTL real no Redis)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin


class ShippingQuote(UUIDPKMixin, Base):
    __tablename__ = "shipping_quotes"

    cache_key: Mapped[str] = mapped_column(String(80), index=True)
    origin_zip: Mapped[str] = mapped_column(String(8))
    dest_zip: Mapped[str] = mapped_column(String(8))
    packages_json: Mapped[list] = mapped_column(JSONB, default=list)
    rates_json: Mapped[list] = mapped_column(JSONB, default=list)
    provider: Mapped[str] = mapped_column(String(40), default="melhor_envio")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
