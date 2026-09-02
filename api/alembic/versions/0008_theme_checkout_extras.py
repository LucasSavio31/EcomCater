"""Checkout: cartão animado, revisão (on/posição), order bump.

Revision ID: 0008_checkout_extras
Revises: 0007_var_ckt_colors
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_checkout_extras"
down_revision: str | None = "0007_var_ckt_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("checkout_animated_card", sa.Boolean(), sa.true()),
    ("checkout_show_review", sa.Boolean(), sa.true()),
    ("checkout_review_position", sa.String(8), sa.text("'side'")),
    ("checkout_orderbump_enabled", sa.Boolean(), sa.false()),
    ("checkout_orderbump_product_id", sa.String(36), None),
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
        col = (
            sa.Column(name, type_, nullable=True)
            if default is None
            else sa.Column(name, type_, nullable=False, server_default=default)
        )
        op.add_column("theme_settings", col)


def downgrade() -> None:
    have = _existing()
    for name, _, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
