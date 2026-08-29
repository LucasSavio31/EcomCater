"""Modelo do módulo `banners` — vitrines/banners da home por slot e período."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

BANNER_SLOTS = ("top_bar", "hero", "showcase", "size_shortcuts", "footer")


class Banner(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "banners"

    slot: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str | None] = mapped_column(String(160))
    image_desktop_key: Mapped[str | None] = mapped_column(String(300))
    image_mobile_key: Mapped[str | None] = mapped_column(String(300))
    link_url: Mapped[str | None] = mapped_column(String(500))
    alt: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
