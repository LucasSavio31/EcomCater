"""Logo próprio do popup de captura de leads.

Revision ID: 0038_lead_popup_logo
Revises: 0037_system_backup_health
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0038_lead_popup_logo"
down_revision: str | None = "0037_system_backup_health"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    cols = _cols()
    if not cols:
        return
    if "lead_popup_logo_key" not in cols:
        op.add_column(_TABLE, sa.Column("lead_popup_logo_key", sa.String(300), nullable=True))
    if "lead_popup_show_logo" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("lead_popup_show_logo", sa.Boolean(), nullable=False, server_default="true"),
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("lead_popup_logo_key", "lead_popup_show_logo"):
        if name in cols:
            op.drop_column(_TABLE, name)
