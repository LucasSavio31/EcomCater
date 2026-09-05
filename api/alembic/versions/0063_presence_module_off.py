"""Módulo `presence` (visitantes ao vivo) começa DESLIGADO.

`require_module_enabled` só bloqueia quando já existe uma linha em `modules`
com `enabled=false` — sem linha, trata como ligado (independente do
`default_enabled` do ModuleSpec). Como esse módulo faz rastreamento por IP,
precisamos que ele comece desligado de fato até o lojista ativar
conscientemente em Módulos, então semeamos a linha aqui em vez de confiar
só no default do registro.

Revision ID: 0063_presence_module_off
Revises: 0062_button_border_colors
Create Date: 2026-09-05

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0063_presence_module_off"
down_revision: str | None = "0062_button_border_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM modules WHERE slug = 'presence'")
    ).first()
    if not exists:
        conn.execute(
            sa.text(
                "INSERT INTO modules (slug, enabled, config_json) "
                "VALUES ('presence', false, '{}'::jsonb)"
            )
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM modules WHERE slug = 'presence'"))
