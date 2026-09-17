"""Sininho de notificações do admin (novas vendas, novos envios).

Revision ID: 0068_notifications
Revises: 0067_woocommerce_bridge
Create Date: 2026-09-17

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0068_notifications"
down_revision: str | None = "0067_woocommerce_bridge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "notifications" not in _tables():
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("type", sa.String(40), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("message", sa.String(400), nullable=True),
            sa.Column("link_path", sa.String(300), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    if "notifications" in _tables():
        op.drop_table("notifications")
