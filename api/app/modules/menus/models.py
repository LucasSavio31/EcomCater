"""Modelos do módulo `menus` — menu superior (com mega menu) e rodapé."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

MENU_LOCATIONS = ("header", "footer")
LINK_TYPES = ("category", "url", "page")


class Menu(UUIDPKMixin, Base):
    __tablename__ = "menus"

    location: Mapped[str] = mapped_column(String(10), index=True)
    name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list[MenuItem]] = relationship(
        back_populates="menu", cascade="all, delete-orphan", order_by="MenuItem.position"
    )


class MenuItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "menu_items"

    menu_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(String(120))
    link_type: Mapped[str] = mapped_column(String(10), default="url")
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)

    is_megamenu: Mapped[bool] = mapped_column(Boolean, default=False)
    highlight: Mapped[bool] = mapped_column(Boolean, default=False)
    show_size_shortcuts: Mapped[bool] = mapped_column(Boolean, default=False)
    size_shortcut_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )

    menu: Mapped[Menu] = relationship(back_populates="items")
    parent: Mapped[MenuItem | None] = relationship(
        "MenuItem", remote_side="MenuItem.id", back_populates="children"
    )
    children: Mapped[list[MenuItem]] = relationship(
        "MenuItem", back_populates="parent", cascade="all, delete-orphan",
        order_by="MenuItem.position",
    )
