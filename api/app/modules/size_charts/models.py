"""Modelo do módulo `size_charts` — tabelas de medidas."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin


class SizeChart(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "size_charts"

    name: Mapped[str] = mapped_column(String(120))
    # cabeçalho da tabela (ex.: ["Tam", "Pé (cm)", "Palmilha (cm)"])
    columns: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    # linhas — cada uma com o mesmo nº de células das colunas
    rows: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    note: Mapped[str | None] = mapped_column(String(400))
