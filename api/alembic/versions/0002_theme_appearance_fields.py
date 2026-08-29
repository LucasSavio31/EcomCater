"""Campos de aparência do tema: cores de botão, header, footer e largura do header.

Revision ID: 0002_theme_appearance
Revises: 0001_initial
Create Date: 2026-08-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_theme_appearance"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("button_bg_color", sa.String(9), "#111111"),
    ("button_text_color", sa.String(9), "#FFFFFF"),
    ("button_hover_color", sa.String(9), "#DC2626"),
    ("header_bg_color", sa.String(9), "#FFFFFF"),
    ("header_text_color", sa.String(9), "#111827"),
    ("footer_bg_color", sa.String(9), "#111827"),
    ("footer_text_color", sa.String(9), "#E5E7EB"),
]


def upgrade() -> None:
    for name, type_, default in _COLUMNS:
        op.add_column(
            "theme_settings",
            sa.Column(name, type_, nullable=False, server_default=default),
        )
    op.add_column(
        "theme_settings",
        sa.Column("header_max_width_px", sa.Integer(), nullable=False, server_default="1280"),
    )
    # remove os server_default (o app cuida dos defaults daqui pra frente)
    for name, _, _ in _COLUMNS:
        op.alter_column("theme_settings", name, server_default=None)
    op.alter_column("theme_settings", "header_max_width_px", server_default=None)


def downgrade() -> None:
    for name, _, _ in _COLUMNS:
        op.drop_column("theme_settings", name)
    op.drop_column("theme_settings", "header_max_width_px")
