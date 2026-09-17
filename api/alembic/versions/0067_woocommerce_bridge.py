"""Camada de compatibilidade com a REST API do WooCommerce (`/wp-json/wc/v3`)
-- é assim que ERPs como o Bling enxergam a loja (usam o app pronto
"WooCommerce" deles, em vez de uma integração sob medida).

- `orders.wc_id` / `products.wc_id` / `product_variants.wc_id`: id inteiro
  estável (sequência própria por tabela) -- a API do WooCommerce só fala
  com inteiros, nunca UUID; gerado uma vez, nunca muda.
- `woo_keys`: Consumer Key/Secret (Configurações > API REST do WooCommerce
  de verdade) -- o segredo é guardado só como hash (mesma lógica de senha),
  mostrado em texto puro uma única vez, na hora da criação.
- `woo_webhooks`: assinaturas de webhook que o próprio Bling cria via
  `POST /wp-json/wc/v3/webhooks` -- é assim que a loja avisa o Bling na
  hora (pedido criado/pago/mudou de status), sem polling.

Revision ID: 0067_woocommerce_bridge
Revises: 0066_domains_cache_pages
Create Date: 2026-09-17

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence as SequenceABC

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0067_woocommerce_bridge"
down_revision: str | None = "0066_domains_cache_pages"
branch_labels: str | SequenceABC[str] | None = None
depends_on: str | SequenceABC[str] | None = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _add_wc_id(table: str, seq_name: str) -> None:
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
    if "wc_id" not in _cols(table):
        op.add_column(
            table,
            sa.Column(
                "wc_id",
                sa.BigInteger(),
                server_default=sa.text(f"nextval('{seq_name}')"),
                nullable=False,
            ),
        )
        op.execute(f"ALTER SEQUENCE {seq_name} OWNED BY {table}.wc_id")
        op.create_unique_constraint(f"uq_{table}_wc_id", table, ["wc_id"])


def upgrade() -> None:
    _add_wc_id("orders", "orders_wc_id_seq")
    _add_wc_id("products", "products_wc_id_seq")
    _add_wc_id("product_variants", "product_variants_wc_id_seq")

    existing = _tables()

    if "woo_keys" not in existing:
        op.create_table(
            "woo_keys",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("consumer_key", sa.String(64), nullable=False, unique=True),
            sa.Column("consumer_secret_hash", sa.String(128), nullable=False),
            sa.Column("description", sa.String(160), nullable=True),
            sa.Column("permission", sa.String(12), nullable=False, server_default="read_write"),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if "woo_webhooks" not in existing:
        op.create_table(
            "woo_webhooks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(200), nullable=True),
            sa.Column("topic", sa.String(60), nullable=False),
            sa.Column("delivery_url", sa.String(500), nullable=False),
            sa.Column("secret", sa.String(200), nullable=False),
            sa.Column("status", sa.String(12), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    if "woo_webhooks" in _tables():
        op.drop_table("woo_webhooks")
    if "woo_keys" in _tables():
        op.drop_table("woo_keys")
    for table, seq in (
        ("product_variants", "product_variants_wc_id_seq"),
        ("products", "products_wc_id_seq"),
        ("orders", "orders_wc_id_seq"),
    ):
        if "wc_id" in _cols(table):
            op.drop_constraint(f"uq_{table}_wc_id", table, type_="unique")
            op.drop_column(table, "wc_id")
        op.execute(f"DROP SEQUENCE IF EXISTS {seq}")
