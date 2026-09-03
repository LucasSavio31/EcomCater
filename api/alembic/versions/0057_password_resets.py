"""Tabela password_resets (redefinição de senha — cliente e admin).

Revision ID: 0057_password_resets
Revises: 0056_ga4_api_secret
Create Date: 2026-09-03

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0057_password_resets"
down_revision: str | None = "0056_ga4_api_secret"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "password_resets"


def _has_table() -> bool:
    return _TABLE in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_type", sa.String(10), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_resets_token_hash", _TABLE, ["token_hash"], unique=True)
    op.create_index("ix_password_resets_subject_type", _TABLE, ["subject_type"])
    op.create_index("ix_password_resets_subject_id", _TABLE, ["subject_id"])


def downgrade() -> None:
    if _has_table():
        op.drop_table(_TABLE)
