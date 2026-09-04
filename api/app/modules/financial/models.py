"""Livro-caixa financeiro — append-only, independente da tabela `orders`.

Cada fato financeiro (pedido feito / pago / estornado / cancelado) grava uma
linha aqui. Excluir um pedido não apaga o histórico: faturamento, estorno,
cancelamento e total de pedidos são sempre cumulativos.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin

# placed  = pedido criado          (conta em "total de pedidos")
# paid    = pagamento confirmado   (conta em "faturamento bruto")
# refunded= estorno
# canceled= cancelamento
FINANCIAL_KINDS = ("placed", "paid", "refunded", "canceled")


class FinancialEvent(UUIDPKMixin, Base):
    __tablename__ = "financial_events"
    __table_args__ = (
        UniqueConstraint("order_number", "kind", name="uq_financial_events_order_kind"),
    )

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    order_number: Mapped[str] = mapped_column(String(20))
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL")
    )
    gross_cents: Mapped[int] = mapped_column(Integer, default=0)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
