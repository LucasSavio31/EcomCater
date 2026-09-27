"""Multi-domínio nas integrações: chaves/webhooks do WooCommerce por domínio.

Revision ID: 0087_woo_per_domain
Revises: 0086_smtp_per_domain
Create Date: 2026-09-26

Idempotente. Só ADICIONA colunas nulas -- chaves/webhooks existentes ficam
no domínio principal (NULL), ERP atual continua igual.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0087_woo_per_domain"
down_revision: str | None = "0086_smtp_per_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table in ("woo_keys", "woo_webhooks"):
        if "hostname" not in _cols(table):
            op.add_column(table, sa.Column("hostname", sa.String(255), nullable=True))


def downgrade() -> None:
    for table in ("woo_keys", "woo_webhooks"):
        if "hostname" in _cols(table):
            op.drop_column(table, "hostname")
