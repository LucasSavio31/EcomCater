"""Campos de aparência do tema: cores de botão, header, footer e largura do header.

Revision ID: 0002_theme_appearance
Revises: 0001_initial
Create Date: 2026-08-29

Idempotente: só adiciona a coluna que ainda não existir. Assim a migration
funciona tanto num banco antigo (criado antes destes campos) quanto num banco
novo, onde a `0001` já cria o schema atual inteiro via `Base.metadata`.
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
    ("header_max_width_px", sa.Integer(), "1280"),
]


def _existing_columns() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing_columns()
    added: list[str] = []
    for name, type_, default in _COLUMNS:
        if name in have:
            continue
        op.add_column(
            "theme_settings",
            sa.Column(name, type_, nullable=False, server_default=default),
        )
        added.append(name)
    # o app cuida dos defaults daqui pra frente
    for name in added:
        op.alter_column("theme_settings", name, server_default=None)


def downgrade() -> None:
    have = _existing_columns()
    for name, _, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
