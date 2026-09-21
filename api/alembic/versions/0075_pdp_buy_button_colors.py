"""Cores próprias do botão "Comprar" da página do produto (independentes do
botão geral em Cores gerais) + espessura de borda (px) configurável pros dois
(antes era sempre 2px fixo).

Revision ID: 0075_pdp_buy_button_colors
Revises: 0074_theme_sound_toggles
Create Date: 2026-09-20

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0075_pdp_buy_button_colors"
down_revision: str | None = "0074_theme_sound_toggles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("pdp_buy_button_bg_color", sa.String(9), "#111111"),
    ("pdp_buy_button_text_color", sa.String(9), "#FFFFFF"),
    ("pdp_buy_button_hover_color", sa.String(9), "#333333"),
    ("pdp_buy_button_border_color", sa.String(9), "#111111"),
)


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    cols = _cols()
    for name, coltype, default in _COLUMNS:
        if name not in cols:
            op.add_column(
                "theme_settings",
                sa.Column(name, coltype, nullable=False, server_default=default),
            )
    if "pdp_buy_button_radius_px" not in cols:
        op.add_column(
            "theme_settings",
            sa.Column("pdp_buy_button_radius_px", sa.Integer(), nullable=False, server_default="12"),
        )
    if "pdp_buy_button_border_width_px" not in cols:
        op.add_column(
            "theme_settings",
            sa.Column("pdp_buy_button_border_width_px", sa.Integer(), nullable=False, server_default="2"),
        )
    if "button_border_width_px" not in cols:
        op.add_column(
            "theme_settings",
            sa.Column("button_border_width_px", sa.Integer(), nullable=False, server_default="2"),
        )


def downgrade() -> None:
    cols = _cols()
    names = [c[0] for c in _COLUMNS] + [
        "pdp_buy_button_radius_px",
        "pdp_buy_button_border_width_px",
        "button_border_width_px",
    ]
    for name in names:
        if name in cols:
            op.drop_column("theme_settings", name)
