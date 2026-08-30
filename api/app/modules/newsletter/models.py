"""Modelo do módulo `newsletter` — inscritos para promoções."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin


class NewsletterSubscriber(UUIDPKMixin, Base):
    __tablename__ = "newsletter_subscribers"

    email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(40), default="home_form")
    coupon_code: Mapped[str | None] = mapped_column(String(60))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
