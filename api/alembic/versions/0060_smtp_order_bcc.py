"""smtp_settings.order_bcc — cópia oculta dos e-mails de pedido do cliente.

Revision ID: 0060_smtp_order_bcc
Revises: 0059_email_log_retry_queue
Create Date: 2026-09-03

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0060_smtp_order_bcc"
down_revision: str | None = "0059_email_log_retry_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "smtp_settings"
_COL = "order_bcc"


def _has_col() -> bool:
    return any(c["name"] == _COL for c in sa.inspect(op.get_bind()).get_columns(_TABLE))


def upgrade() -> None:
    if not _has_col():
        op.add_column(_TABLE, sa.Column(_COL, sa.String(200), nullable=True))


def downgrade() -> None:
    if _has_col():
        op.drop_column(_TABLE, _COL)
