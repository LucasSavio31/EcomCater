"""Extensão `unaccent` — buscas textuais ignoram acentos em todo o site.

Revision ID: 0054_unaccent_extension
Revises: 0053_checkout_notes
Create Date: 2026-09-01

Idempotente. Só cria a extensão (usada por app.shared.search).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0054_unaccent_extension"
down_revision: str | None = "0053_checkout_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    # A extensão pode estar em uso por índices/consultas; não removemos.
    pass
