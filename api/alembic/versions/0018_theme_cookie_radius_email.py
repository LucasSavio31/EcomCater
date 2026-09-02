"""theme_settings: raio de botão, aviso de cookies e identidade dos e-mails.

Revision ID: 0018_theme_extras
Revises: 0017_stock_nullable
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_theme_extras"
down_revision: str | None = "0017_stock_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COOKIE_TXT = (
    "Usamos cookies para melhorar sua experiência. Ao continuar, você concorda "
    "com a nossa política de privacidade."
)

_COLS: list[tuple[str, sa.types.TypeEngine, str]] = [
    ("button_radius_px", sa.Integer(), "12"),
    ("cookie_consent_enabled", sa.Boolean(), sa.false()),
    ("cookie_consent_text", sa.String(400), _COOKIE_TXT),
    ("email_header_bg_color", sa.String(9), "#111111"),
    ("email_header_text_color", sa.String(9), "#FFFFFF"),
    ("email_body_bg_color", sa.String(9), "#FFFFFF"),
    ("email_text_color", sa.String(9), "#111827"),
    ("email_button_color", sa.String(9), "#111111"),
    ("email_button_text_color", sa.String(9), "#FFFFFF"),
    ("email_footer_text", sa.String(300), ""),
]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name, type_, default in _COLS:
        if name in have:
            continue
        op.add_column(
            "theme_settings",
            sa.Column(name, type_, nullable=False, server_default=default),
        )


def downgrade() -> None:
    have = _existing()
    for name, _type, _default in _COLS:
        if name in have:
            op.drop_column("theme_settings", name)
