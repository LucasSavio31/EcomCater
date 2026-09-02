"""Bloco de reassurance da PDP (ligar/desligar + itens editáveis).

Revision ID: 0040_pdp_reassurance
Revises: 0039_variation_radius
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0040_pdp_reassurance"
down_revision: str | None = "0039_variation_radius"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_DEFAULT = (
    '["\\ud83d\\udd04 Troca fácil em até 30 dias", '
    '"\\ud83d\\udd12 Site 100% seguro — pagamento criptografado", '
    '"\\ud83d\\udce6 Enviamos para todo o Brasil pelos Correios"]'
)


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    cols = _cols()
    if not cols:
        return
    if "pdp_reassurance_enabled" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("pdp_reassurance_enabled", sa.Boolean(), nullable=False, server_default="true"),
        )
    if "pdp_reassurance_items" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("pdp_reassurance_items", JSONB, nullable=False, server_default=_DEFAULT),
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("pdp_reassurance_items", "pdp_reassurance_enabled"):
        if name in cols:
            op.drop_column(_TABLE, name)
