"""Sininho de notificações do admin: novas vendas e novos envios, hoje --
extensível pra outros tipos depois. Compartilhado entre todo admin (não é
por usuário -- é o mesmo painel, mesma equipe pequena)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

NOTIFICATION_TYPES = ("order_created", "order_shipped")


class Notification(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_created_at", "created_at"),)

    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(String(400))
    # caminho relativo no admin pra abrir o item específico ao clicar
    # (ex.: "/pedidos/2026-000001").
    link_path: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
