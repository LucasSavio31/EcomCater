"""Tabela `nfe_documents` -- rastreia cada NF-e emitida por pedido (status,
chave de acesso, protocolo, XML/DANFE no private_storage).

Revision ID: 0073_nfe_documents
Revises: 0072_nfe_product_fiscal
Create Date: 2026-09-19

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0073_nfe_documents"
down_revision: str | None = "0072_nfe_product_fiscal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("nfe_documents"):
        return
    op.create_table(
        "nfe_documents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE", name="fk_nfe_documents_order_id_orders"),
            nullable=False,
        ),
        sa.Column("order_number", sa.String(40), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("ambiente", sa.String(12), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("serie", sa.Integer(), nullable=True),
        sa.Column("chave_acesso", sa.String(44), nullable=True),
        sa.Column("protocolo_autorizacao", sa.String(20), nullable=True),
        sa.Column("recibo", sa.String(20), nullable=True),
        sa.Column("xml_key", sa.String(255), nullable=True),
        sa.Column("danfe_key", sa.String(255), nullable=True),
        sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "requested_by_admin_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey(
                "admin_users.id", ondelete="SET NULL", name="fk_nfe_documents_requested_by_admin_id_admin_users"
            ),
            nullable=True,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_justificativa", sa.Text(), nullable=True),
    )
    op.create_index("ix_nfe_documents_order_id", "nfe_documents", ["order_id"])
    op.create_index("ix_nfe_documents_order_number", "nfe_documents", ["order_number"])


def downgrade() -> None:
    if _has_table("nfe_documents"):
        op.drop_table("nfe_documents")
