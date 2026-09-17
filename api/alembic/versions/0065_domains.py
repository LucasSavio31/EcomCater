"""Domínios próprios — proxy reverso automático (aaPanel) + SSL.

- domains  (hostname raiz; admin./api. são derivados em código, não linhas)

Revision ID: 0065_domains
Revises: 0064_order_reverse_shipping
Create Date: 2026-09-17

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0065_domains"
down_revision: str | None = "0064_order_reverse_shipping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "domains" not in _tables():
        op.create_table(
            "domains",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("hostname", sa.String(255), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column(
                "dns_managed_by_cloudflare", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("ssl_status", sa.String(20), nullable=False, server_default="none"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cloudflare_zone_id", sa.String(64), nullable=True),
            sa.Column("cloudflare_nameservers", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("dns_confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("hostname", name="uq_domains_hostname"),
        )
        op.create_index("ix_domains_hostname", "domains", ["hostname"])


def downgrade() -> None:
    if "domains" in _tables():
        op.drop_table("domains")
