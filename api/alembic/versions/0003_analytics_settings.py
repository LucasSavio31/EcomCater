"""Tabela `analytics_settings` — tags de marketing (GTM, GA4, Google Ads, Meta).

Revision ID: 0003_analytics
Revises: 0002_theme_appearance
Create Date: 2026-08-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_analytics"
down_revision: str | None = "0002_theme_appearance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "analytics_settings" in insp.get_table_names():
        op.execute(
        "INSERT INTO analytics_settings "
        "(id, gtm_enabled, ga4_enabled, google_ads_enabled, meta_pixel_enabled, meta_capi_enabled) "
        "VALUES (1, false, false, false, false, false) ON CONFLICT DO NOTHING"
    )
        return
    op.create_table(
        "analytics_settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("gtm_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gtm_container_id", sa.String(length=20), nullable=True),
        sa.Column("ga4_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ga4_measurement_id", sa.String(length=20), nullable=True),
        sa.Column("google_ads_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("google_ads_conversion_id", sa.String(length=20), nullable=True),
        sa.Column("google_ads_purchase_label", sa.String(length=60), nullable=True),
        sa.Column("meta_pixel_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("meta_pixel_id", sa.String(length=32), nullable=True),
        sa.Column("meta_capi_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("meta_capi_access_token", sa.Text(), nullable=True),
        sa.Column("meta_test_event_code", sa.String(length=40), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_analytics_settings_singleton"),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_settings"),
    )
    op.execute(
        "INSERT INTO analytics_settings "
        "(id, gtm_enabled, ga4_enabled, google_ads_enabled, meta_pixel_enabled, meta_capi_enabled) "
        "VALUES (1, false, false, false, false, false) ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("analytics_settings")
