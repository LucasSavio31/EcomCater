"""Classificação fiscal por produto (NF-e): NCM/CFOP/CEST/CSOSN-CST/origem/
unidade -- nenhum campo fiscal existia em `products` até aqui.

Revision ID: 0072_nfe_product_fiscal
Revises: 0071_nfe_store_fiscal
Create Date: 2026-09-19

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0072_nfe_product_fiscal"
down_revision: str | None = "0071_nfe_store_fiscal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("products")}


def upgrade() -> None:
    cols = _cols()
    if "ncm" not in cols:
        op.add_column("products", sa.Column("ncm", sa.String(8), nullable=True))
    if "cfop" not in cols:
        op.add_column("products", sa.Column("cfop", sa.String(4), nullable=True))
    if "cest" not in cols:
        op.add_column("products", sa.Column("cest", sa.String(7), nullable=True))
    if "csosn_cst" not in cols:
        op.add_column("products", sa.Column("csosn_cst", sa.String(3), nullable=True))
    if "origem" not in cols:
        op.add_column(
            "products", sa.Column("origem", sa.String(1), nullable=False, server_default="0")
        )
    if "unidade" not in cols:
        op.add_column(
            "products", sa.Column("unidade", sa.String(6), nullable=False, server_default="UN")
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("ncm", "cfop", "cest", "csosn_cst", "origem", "unidade"):
        if name in cols:
            op.drop_column("products", name)
