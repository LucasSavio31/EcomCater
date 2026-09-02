"""Banner hero (liga/desliga + modo) e selos do rodapé em theme_settings.

Revision ID: 0004_hero_seals
Revises: 0003_analytics
Create Date: 2026-08-29

Idempotente: só adiciona a coluna que ainda não existe.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0004_hero_seals"
down_revision: str | None = "0003_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("hero_enabled", sa.Boolean(), sa.true()),
    ("hero_mode", sa.String(12), sa.text("'carousel'")),
    ("hero_autoplay_seconds", sa.Integer(), sa.text("5")),
    ("footer_seals_enabled", sa.Boolean(), sa.true()),
    ("footer_seals_json", JSONB(), sa.text("'{}'::jsonb")),
]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name, type_, default in _COLUMNS:
        if name in have:
            continue
        op.add_column(
            "theme_settings",
            sa.Column(name, type_, nullable=False, server_default=default),
        )


def downgrade() -> None:
    have = _existing()
    for name, _, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
