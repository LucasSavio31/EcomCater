"""Modelo do módulo `nfe`: rastreamento de cada NF-e emitida por pedido.

Não é único por pedido de propósito -- cancelar e reemitir gera uma nova
`NfeDocument` (a chave de acesso muda), a antiga fica como histórico
(`status="canceled"`). `service.latest_for_order()` é quem decide qual é "a"
nota atual do pedido.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

# status: pending -> processing -> authorized | rejected | error
#         authorized -> canceled (evento de cancelamento, dentro do prazo legal)
NFE_STATUSES = ("pending", "processing", "authorized", "rejected", "canceled", "error")


class NfeDocument(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "nfe_documents"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    order_number: Mapped[str] = mapped_column(String(40), index=True)

    status: Mapped[str] = mapped_column(String(12), default="pending")
    status_message: Mapped[str | None] = mapped_column(Text)
    ambiente: Mapped[str] = mapped_column(String(12))  # homologacao | producao (snapshot)

    numero: Mapped[int | None] = mapped_column(Integer)
    serie: Mapped[int | None] = mapped_column(Integer)
    chave_acesso: Mapped[str | None] = mapped_column(String(44))
    protocolo_autorizacao: Mapped[str | None] = mapped_column(String(20))
    recibo: Mapped[str | None] = mapped_column(String(20))  # nº do recibo do lote, p/ consultar

    # chaves no private_storage (nunca URL pública)
    xml_key: Mapped[str | None] = mapped_column(String(255))
    danfe_key: Mapped[str | None] = mapped_column(String(255))

    total_cents: Mapped[int] = mapped_column(Integer, default=0)

    # Payload exatamente como foi submetido (já com eventuais edições manuais
    # do admin na hora de emitir) -- serve de auditoria e permite reenviar sem
    # precisar re-derivar tudo do pedido/produto (que podem ter mudado desde).
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    requested_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_justificativa: Mapped[str | None] = mapped_column(Text)
