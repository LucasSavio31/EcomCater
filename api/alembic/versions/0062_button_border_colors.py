"""Cor de borda opcional pro botão "Comprar" (loja) e pros botões do checkout
(finalizar + etapas). Igual à cor de fundo por padrão -> some visualmente até
o lojista escolher uma cor diferente.

Revision ID: 0062_button_border_colors
Revises: 0061_financial_ledger
Create Date: 2026-09-05

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0062_button_border_colors"
down_revision: str | None = "0061_financial_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("button_border_color", "#111111"),
    ("checkout_button_border_color", "#FFC400"),
    ("checkout_step_button_border_color", "#FFC400"),
]


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    existing = _cols()
    for name, default in _COLUMNS:
        if name not in existing:
            op.add_column(
                "theme_settings",
                sa.Column(
                    name, sa.String(9), nullable=False, server_default=default
                ),
            )


def downgrade() -> None:
    existing = _cols()
    for name, _default in _COLUMNS:
        if name in existing:
            op.drop_column("theme_settings", name)
