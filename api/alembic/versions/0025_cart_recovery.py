"""cart_recovery: recovery_messages + abandoned_carts.

Revision ID: 0025_cart_recovery
Revises: 0024_coupon_audience
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_cart_recovery"
down_revision: str | None = "0024_coupon_audience"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    have = _tables()
    if "recovery_messages" not in have:
        op.create_table(
            "recovery_messages",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("delay_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("subject", sa.String(200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "abandoned_carts" not in have:
        op.create_table(
            "abandoned_carts",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("email", sa.String(200), nullable=False, index=True),
            sa.Column("cart_id", sa.UUID(), sa.ForeignKey("carts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("cart_token", sa.String(64), nullable=False),
            sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("items_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_email_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reminders_sent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("order_id", sa.UUID(), nullable=True),
        )


def downgrade() -> None:
    have = _tables()
    if "abandoned_carts" in have:
        op.drop_table("abandoned_carts")
    if "recovery_messages" in have:
        op.drop_table("recovery_messages")
