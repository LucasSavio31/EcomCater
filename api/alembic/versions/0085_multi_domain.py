"""Multi-domínio: cada domínio com as próprias tags/verificação/SEO.

- `orders.domain_name`: só informativo, de qual domínio o pedido veio;
- `analytics_settings` (domínio principal) ganha SEO do site
  (`seo_title`, `seo_description`, `seo_noindex`);
- `analytics_site_settings`: mesmos campos, uma linha por domínio EXTRA
  (chave = hostname). Domínio sem linha = tudo desligado.

Revision ID: 0085_multi_domain
Revises: 0084_product_supplier_model
Create Date: 2026-09-26

Idempotente. Só ADICIONA -- nenhum dado existente muda.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0085_multi_domain"
down_revision: str | None = "0084_product_supplier_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _seo_columns() -> list[sa.Column]:
    return [
        sa.Column("seo_title", sa.String(200), nullable=True),
        sa.Column("seo_description", sa.String(320), nullable=True),
        sa.Column("seo_noindex", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]


def _flag(name: str) -> sa.Column:
    return sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())


def upgrade() -> None:
    bind = op.get_bind()

    if "domain_name" not in _cols("orders"):
        op.add_column("orders", sa.Column("domain_name", sa.String(255), nullable=True))

    existing = _cols("analytics_settings")
    for col in _seo_columns():
        if col.name not in existing:
            op.add_column("analytics_settings", col)

    if "analytics_site_settings" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "analytics_site_settings",
            sa.Column("hostname", sa.String(255), primary_key=True),
            _flag("gtm_enabled"),
            sa.Column("gtm_container_id", sa.String(20)),
            _flag("ga4_enabled"),
            sa.Column("ga4_measurement_id", sa.String(20)),
            sa.Column("ga4_api_secret", sa.Text()),
            _flag("google_ads_enabled"),
            sa.Column("google_ads_conversion_id", sa.String(20)),
            sa.Column("google_ads_purchase_label", sa.String(60)),
            _flag("meta_pixel_enabled"),
            sa.Column("meta_pixel_id", sa.String(32)),
            _flag("meta_capi_enabled"),
            sa.Column("meta_capi_access_token", sa.Text()),
            sa.Column("meta_test_event_code", sa.String(40)),
            _flag("merchant_center_enabled"),
            sa.Column("merchant_center_verification_code", sa.String(100)),
            *_seo_columns(),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "analytics_site_settings" in sa.inspect(bind).get_table_names():
        op.drop_table("analytics_site_settings")
    existing = _cols("analytics_settings")
    for name in ("seo_title", "seo_description", "seo_noindex"):
        if name in existing:
            op.drop_column("analytics_settings", name)
    if "domain_name" in _cols("orders"):
        op.drop_column("orders", "domain_name")
