"""Produto: `supplier_model` -- nome/modelo como o FORNECEDOR conhece a peça
(uso interno: tela do pedido no admin, romaneio, planilha de fornecedor).

Preenche os modelos renomeados na 0083 (FAIRBANKS -> 3010, ROAD -> 3020,
INTRUDER -> 3030) a partir do SKU, que manteve o nome original. Só grava onde
ainda está vazio -- não sobrescreve o que o admin editar.

Revision ID: 0084_product_supplier_model
Revises: 0083_product_slug_redirects
Create Date: 2026-09-26

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0084_product_supplier_model"
down_revision: str | None = "0083_product_slug_redirects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MODELS = ("FAIRBANKS", "ROAD", "INTRUDER")


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("products")}
    if "supplier_model" not in cols:
        op.add_column("products", sa.Column("supplier_model", sa.String(120), nullable=True))

    for model in _MODELS:
        bind.execute(
            sa.text(
                "UPDATE products SET supplier_model = :m "
                "WHERE supplier_model IS NULL AND upper(sku_root) LIKE :pat"
            ),
            {"m": model, "pat": f"%-{model}-%"},
        )


def downgrade() -> None:
    if "supplier_model" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("products")}:
        op.drop_column("products", "supplier_model")
