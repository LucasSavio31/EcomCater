"""Tarja de copyright do rodapé — texto + cores configuráveis.

Revision ID: 0029_footer_copyright
Revises: 0028_topbar_centered
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_footer_copyright"
down_revision: str | None = "0028_topbar_centered"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_DEFAULT_TEXT = "© {ano} {loja} — CNPJ {cnpj}. Todos os Direitos Reservados."
_DEFAULT_NOTE = (
    "Preços e condições de pagamento exclusivos para compras via internet. "
    "Endereço comercial disponível na página Fale conosco."
)


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    cols = _cols()
    if not cols:
        return
    if "footer_note_text" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("footer_note_text", sa.String(500), nullable=False, server_default=_DEFAULT_NOTE),
        )
    if "footer_copyright_enabled" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("footer_copyright_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "footer_copyright_text" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("footer_copyright_text", sa.String(400), nullable=False, server_default=_DEFAULT_TEXT),
        )
    if "footer_copyright_bg_color" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("footer_copyright_bg_color", sa.String(9), nullable=False, server_default="#FFFFFF"),
        )
    if "footer_copyright_text_color" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("footer_copyright_text_color", sa.String(9), nullable=False, server_default="#6B7280"),
        )


def downgrade() -> None:
    cols = _cols()
    for name in (
        "footer_note_text",
        "footer_copyright_enabled",
        "footer_copyright_text",
        "footer_copyright_bg_color",
        "footer_copyright_text_color",
    ):
        if name in cols:
            op.drop_column(_TABLE, name)
