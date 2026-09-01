"""2FA (TOTP) para contas admin.

Revision ID: 0036_admin_2fa
Revises: 0035_size_chart_popup
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0036_admin_2fa"
down_revision: str | None = "0035_size_chart_popup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "admin_users"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    cols = _cols()
    if not cols:
        return
    if "totp_secret" not in cols:
        op.add_column(_TABLE, sa.Column("totp_secret", sa.String(64), nullable=True))
    if "totp_enabled" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )
    if "recovery_codes_json" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("recovery_codes_json", JSONB, nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("totp_secret", "totp_enabled", "recovery_codes_json"):
        if name in cols:
            op.drop_column(_TABLE, name)
