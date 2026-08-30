"""Redes sociais no rodapé — liga/desliga por rede.

Revision ID: 0030_footer_social
Revises: 0029_footer_copyright
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_footer_social"
down_revision: str | None = "0029_footer_copyright"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = (
    "footer_social_instagram_enabled",
    "footer_social_facebook_enabled",
    "footer_social_tiktok_enabled",
    "footer_social_youtube_enabled",
)


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _cols()
    if not existing:
        return
    for name in _COLS:
        if name not in existing:
            op.add_column(
                _TABLE,
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()),
            )


def downgrade() -> None:
    existing = _cols()
    for name in _COLS:
        if name in existing:
            op.drop_column(_TABLE, name)
