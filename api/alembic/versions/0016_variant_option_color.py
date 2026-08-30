"""Eixo de cor: variant_option_types.is_color + variant_option_values.image_id.

Revision ID: 0016_option_color
Revises: 0015_variant_attrs
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_option_color"
down_revision: str | None = "0015_variant_attrs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if "is_color" not in _cols("variant_option_types"):
        op.add_column(
            "variant_option_types",
            sa.Column("is_color", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.alter_column("variant_option_types", "is_color", server_default=None)
    if "image_id" not in _cols("variant_option_values"):
        op.add_column(
            "variant_option_values",
            sa.Column("image_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            "fk_variant_option_values_image",
            "variant_option_values",
            "product_images",
            ["image_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if "image_id" in _cols("variant_option_values"):
        op.drop_constraint(
            "fk_variant_option_values_image", "variant_option_values", type_="foreignkey"
        )
        op.drop_column("variant_option_values", "image_id")
    if "is_color" in _cols("variant_option_types"):
        op.drop_column("variant_option_types", "is_color")
