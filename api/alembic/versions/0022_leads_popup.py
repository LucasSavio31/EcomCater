"""Leads: newsletter_subscribers.phone/coupon_code + theme lead_popup_*.

Revision ID: 0022_leads_popup
Revises: 0021_filters_extra
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_leads_popup"
down_revision: str | None = "0021_filters_extra"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


_THEME_COLS: list[tuple[str, sa.types.TypeEngine, object]] = [
    ("lead_popup_enabled", sa.Boolean(), sa.false()),
    ("lead_capture_enabled", sa.Boolean(), sa.true()),
    ("lead_popup_title", sa.String(160), "Cadastre-se para 10% OFF na primeira compra"),
    ("lead_popup_subtitle", sa.String(280), "Receba promoções e conteúdos exclusivos."),
    ("lead_popup_coupon_code", sa.String(60), None),
    ("lead_popup_bg_color", sa.String(9), "#FFFFFF"),
    ("lead_popup_text_color", sa.String(9), "#111827"),
    ("lead_popup_button_color", sa.String(9), "#F5B301"),
    ("lead_popup_button_text_color", sa.String(9), "#111111"),
]


def upgrade() -> None:
    subs = _cols("newsletter_subscribers")
    if subs:
        if "phone" not in subs:
            op.add_column("newsletter_subscribers", sa.Column("phone", sa.String(32), nullable=True))
        if "coupon_code" not in subs:
            op.add_column(
                "newsletter_subscribers", sa.Column("coupon_code", sa.String(60), nullable=True)
            )

    have = _cols("theme_settings")
    for name, type_, default in _THEME_COLS:
        if name in have:
            continue
        if default is not None:
            op.add_column(
                "theme_settings",
                sa.Column(name, type_, nullable=False, server_default=default),
            )
        else:
            op.add_column("theme_settings", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    have = _cols("theme_settings")
    for name, _t, _d in _THEME_COLS:
        if name in have:
            op.drop_column("theme_settings", name)
    subs = _cols("newsletter_subscribers")
    for name in ("phone", "coupon_code"):
        if name in subs:
            op.drop_column("newsletter_subscribers", name)
