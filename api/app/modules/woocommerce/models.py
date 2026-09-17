"""Modelos do módulo `woocommerce`: chaves da API REST (Consumer Key/Secret,
igual Configurações > API REST > Adicionar chave do WooCommerce de verdade)
e assinaturas de webhook (criadas pelo próprio ERP via `POST .../webhooks`)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

PERMISSIONS = ("read", "write", "read_write")
WEBHOOK_STATUSES = ("active", "paused", "disabled")

# Tópicos que a loja de fato dispara -- os únicos eventos de pedido que
# temos hoje no event bus interno (`order.created`/`order.paid`/
# `order.status_changed`). Um app pode assinar qualquer um; os demais
# tópicos do WooCommerce "de verdade" (produto, cliente, cupom) não têm
# emissor aqui ainda.
WEBHOOK_TOPICS = ("order.created", "order.updated", "order.deleted")


class WooKey(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "woo_keys"

    consumer_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    consumer_secret_hash: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(160))
    permission: Mapped[str] = mapped_column(String(12), default="read_write")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WooWebhook(Base):
    __tablename__ = "woo_webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(60))
    delivery_url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
