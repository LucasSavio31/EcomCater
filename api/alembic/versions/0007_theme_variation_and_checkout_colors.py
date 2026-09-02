"""Cores das variações (PDP) e cores próprias do checkout.

Revision ID: 0007_var_ckt_colors
Revises: 0006_checkout_model
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_var_ckt_colors"
down_revision: str | None = "0006_checkout_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("variation_bg_color", "#FDE047"),
    ("variation_text_color", "#111111"),
    ("variation_border_color", "#111111"),
    ("checkout_bg_color", "#F7F7F7"),
    ("checkout_header_text_color", "#111827"),
    ("checkout_button_text_color", "#FFFFFF"),
    ("checkout_accent_color", "#111111"),
    ("checkout_footer_bg_color", "#111827"),
    ("checkout_footer_text_color", "#E5E7EB"),
]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name, default in _COLUMNS:
        if name in have:
            continue
        op.add_column(
            "theme_settings",
            sa.Column(name, sa.String(9), nullable=False, server_default=default),
        )


def downgrade() -> None:
    have = _existing()
    for name, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
