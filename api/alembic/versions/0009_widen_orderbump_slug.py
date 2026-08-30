"""Alarga checkout_orderbump_product_id (guarda o slug do produto).

Revision ID: 0009_orderbump_slug
Revises: 0008_checkout_extras
Create Date: 2026-08-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_orderbump_slug"
down_revision: str | None = "0008_checkout_extras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("theme_settings") as batch:
        batch.alter_column(
            "checkout_orderbump_product_id",
            type_=sa.String(200),
            existing_type=sa.String(36),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("theme_settings") as batch:
        batch.alter_column(
            "checkout_orderbump_product_id",
            type_=sa.String(36),
            existing_type=sa.String(200),
            existing_nullable=True,
        )
