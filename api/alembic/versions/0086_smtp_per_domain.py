"""SMTP por domínio: e-mails de uma venda saem pelo SMTP vinculado ao
domínio em que ela foi feita. O SMTP de sempre (`smtp_settings`, id=1)
continua sendo o do domínio principal e o fallback.

- `smtp_domain_settings`: um SMTP por domínio extra (chave = hostname);
- `email_log.site_host`: de qual domínio o e-mail saiu (o reenvio da fila
  usa o mesmo SMTP).

Revision ID: 0086_smtp_per_domain
Revises: 0085_multi_domain
Create Date: 2026-09-26

Idempotente. Só ADICIONA.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0086_smtp_per_domain"
down_revision: str | None = "0085_multi_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "smtp_domain_settings" not in insp.get_table_names():
        op.create_table(
            "smtp_domain_settings",
            sa.Column("hostname", sa.String(255), primary_key=True),
            sa.Column("host", sa.String(200)),
            sa.Column("port", sa.Integer()),
            sa.Column("username", sa.String(200)),
            sa.Column("password_enc", sa.Text()),
            sa.Column("use_tls", sa.Boolean(), server_default=sa.true()),
            sa.Column("use_ssl", sa.Boolean(), server_default=sa.false()),
            sa.Column("from_email", sa.String(200)),
            sa.Column("from_name", sa.String(160)),
            sa.Column("order_bcc", sa.String(200)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )
    if "site_host" not in {c["name"] for c in insp.get_columns("email_log")}:
        op.add_column("email_log", sa.Column("site_host", sa.String(255), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "site_host" in {c["name"] for c in insp.get_columns("email_log")}:
        op.drop_column("email_log", "site_host")
    if "smtp_domain_settings" in insp.get_table_names():
        op.drop_table("smtp_domain_settings")
