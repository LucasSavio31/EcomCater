"""`domains.switch_requested_at` -- controla se já pedimos a troca de
domínio primário (arquivo-gatilho pro script do host), pra não pedir de
novo em toda passagem do scheduler.

Revision ID: 0070_domain_switch_trigger
Revises: 0069_financial_shipping_cost
Create Date: 2026-09-18

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0070_domain_switch_trigger"
down_revision: str | None = "0069_financial_shipping_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("domains")}


def upgrade() -> None:
    if "switch_requested_at" not in _cols():
        op.add_column(
            "domains", sa.Column("switch_requested_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    if "switch_requested_at" in _cols():
        op.drop_column("domains", "switch_requested_at")
