"""Dados fiscais da empresa (NF-e): `store_settings.ie`/`regime_tributario`/
`cnae_fiscal`/`municipio_ibge` -- faltavam pra montar o emitente da nota.

Revision ID: 0071_nfe_store_fiscal
Revises: 0070_domain_switch_trigger
Create Date: 2026-09-19

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0071_nfe_store_fiscal"
down_revision: str | None = "0070_domain_switch_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("store_settings")}


def upgrade() -> None:
    cols = _cols()
    if "ie" not in cols:
        op.add_column("store_settings", sa.Column("ie", sa.String(20), nullable=True))
    if "regime_tributario" not in cols:
        op.add_column(
            "store_settings", sa.Column("regime_tributario", sa.String(1), nullable=True)
        )
    if "cnae_fiscal" not in cols:
        op.add_column("store_settings", sa.Column("cnae_fiscal", sa.String(9), nullable=True))
    if "municipio_ibge" not in cols:
        op.add_column(
            "store_settings", sa.Column("municipio_ibge", sa.String(7), nullable=True)
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("ie", "regime_tributario", "cnae_fiscal", "municipio_ibge"):
        if name in cols:
            op.drop_column("store_settings", name)
