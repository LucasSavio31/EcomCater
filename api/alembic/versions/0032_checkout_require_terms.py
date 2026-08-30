"""Checkout: liga/desliga o aceite de política de vendas/privacidade.

Revision ID: 0032_checkout_require_terms
Revises: 0031_checkout_step_colors
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_checkout_require_terms"
down_revision: str | None = "0031_checkout_step_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    if _cols() and "checkout_require_terms" not in _cols():
        op.add_column(
            _TABLE,
            sa.Column(
                "checkout_require_terms", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )


def downgrade() -> None:
    if "checkout_require_terms" in _cols():
        op.drop_column(_TABLE, "checkout_require_terms")
