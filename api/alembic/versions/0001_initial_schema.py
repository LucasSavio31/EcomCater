"""Baseline do schema completo (Fase 1).

Estratégia: o schema inteiro já foi desenhado na Fase 0 e vive nos modelos
SQLAlchemy (`app.models`). Esta baseline cria tudo a partir de `Base.metadata`.
Deltas a partir da Fase 2 entram como migrations autogenerate incrementais.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-29
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
    Base.metadata.create_all(bind=conn)


def downgrade() -> None:
    conn = op.get_bind()
    Base.metadata.drop_all(bind=conn)
