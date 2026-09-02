"""Bloco de newsletter na home (menu "Newsletter" no admin).

Revision ID: 0013_newsletter
Revises: 0012_supplier
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_newsletter"
down_revision: str | None = "0012_supplier"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("newsletter_enabled", sa.Boolean(), sa.true()),
    ("newsletter_title", sa.String(120), sa.text("'Receba novidades e ofertas'")),
    (
        "newsletter_subtitle",
        sa.String(240),
        sa.text("'Cadastre seu e-mail e fique por dentro dos lançamentos.'"),
    ),
    ("newsletter_bg_color", sa.String(9), sa.text("'#F5F5F5'")),
    ("newsletter_text_color", sa.String(9), sa.text("'#111827'")),
    ("newsletter_button_color", sa.String(9), sa.text("'#111111'")),
    ("newsletter_button_text_color", sa.String(9), sa.text("'#FFFFFF'")),
]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name, type_, default in _COLUMNS:
        if name not in have:
            op.add_column(
                "theme_settings",
                sa.Column(name, type_, nullable=False, server_default=default),
            )


def downgrade() -> None:
    have = _existing()
    for name, _, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
