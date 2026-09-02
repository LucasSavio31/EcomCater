"""theme_settings.checkout_orderbump_product_ids (JSONB list).

Revision ID: 0020_orderbump_list
Revises: 0019_color_group
Create Date: 2026-08-30

Idempotente. Migra o valor único legado para a lista.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_orderbump_list"
down_revision: str | None = "0019_color_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    if "checkout_orderbump_product_ids" not in _cols():
        op.add_column(
            "theme_settings",
            sa.Column(
                "checkout_orderbump_product_ids",
                sa.dialects.postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
        )
        # migra o slug único legado, se houver
        op.execute(
            "UPDATE theme_settings "
            "SET checkout_orderbump_product_ids = to_jsonb(ARRAY[checkout_orderbump_product_id]) "
            "WHERE checkout_orderbump_product_id IS NOT NULL "
            "AND checkout_orderbump_product_id <> ''"
        )


def downgrade() -> None:
    if "checkout_orderbump_product_ids" in _cols():
        op.drop_column("theme_settings", "checkout_orderbump_product_ids")
