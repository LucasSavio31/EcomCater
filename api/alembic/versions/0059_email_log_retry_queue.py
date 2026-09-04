"""email_log: fila de reenvio (SMTP offline não bloqueia a compra).

Revision ID: 0059_email_log_retry_queue
Revises: 0058_order_processing_error
Create Date: 2026-09-03

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0059_email_log_retry_queue"
down_revision: str | None = "0058_order_processing_error"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "email_log"
_COLS = {
    "attempts": sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    "next_attempt_at": sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    "sent_at": sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    "raw_message": sa.Column("raw_message", sa.LargeBinary(), nullable=True),
}


def _have() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def upgrade() -> None:
    have = _have()
    for name, col in _COLS.items():
        if name not in have:
            op.add_column(_TABLE, col)
    insp = sa.inspect(op.get_bind())
    idx = {i["name"] for i in insp.get_indexes(_TABLE)}
    if "ix_email_log_status_retry" not in idx:
        op.create_index(
            "ix_email_log_status_retry", _TABLE, ["status", "next_attempt_at"]
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ix_email_log_status_retry" in {i["name"] for i in insp.get_indexes(_TABLE)}:
        op.drop_index("ix_email_log_status_retry", _TABLE)
    have = _have()
    for name in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
