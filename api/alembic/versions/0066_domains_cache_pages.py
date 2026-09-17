"""Cache Rules da Cloudflare por domínio — quais tipos de página cachear.

- domains.cache_pages         (JSONB, lista de chaves de CACHE_PAGE_DEFS)
- domains.cache_applied_at    (quando o ruleset foi aplicado pela última vez)

Revision ID: 0066_domains_cache_pages
Revises: 0065_domains
Create Date: 2026-09-17

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0066_domains_cache_pages"
down_revision: str | None = "0065_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    cols = _cols("domains")
    if "cache_pages" not in cols:
        op.add_column("domains", sa.Column("cache_pages", sa.dialects.postgresql.JSONB(), nullable=True))
    if "cache_applied_at" not in cols:
        op.add_column(
            "domains", sa.Column("cache_applied_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    cols = _cols("domains")
    if "cache_applied_at" in cols:
        op.drop_column("domains", "cache_applied_at")
    if "cache_pages" in cols:
        op.drop_column("domains", "cache_pages")
