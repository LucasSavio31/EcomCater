"""Módulo system: backup_settings, backup_records, health_samples.

Revision ID: 0037_system_backup_health
Revises: 0036_admin_2fa
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0037_system_backup_health"
down_revision: str | None = "0036_admin_2fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()

    if "backup_settings" not in tables:
        op.create_table(
            "backup_settings",
            sa.Column("id", sa.SmallInteger(), primary_key=True),
            sa.Column("auto_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("frequency", sa.String(12), nullable=False, server_default="diario"),
            sa.Column("hour", sa.SmallInteger(), nullable=False, server_default="3"),
            sa.Column("keep", sa.SmallInteger(), nullable=False, server_default="7"),
            sa.Column("include_media", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("folder_path", sa.String(500), nullable=True),
            sa.Column("sftp_json", JSONB, nullable=False, server_default="{}"),
            sa.Column("gdrive_json", JSONB, nullable=False, server_default="{}"),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status", sa.String(20), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint("id = 1", name="singleton"),
        )

    if "backup_records" not in tables:
        op.create_table(
            "backup_records",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("status", sa.String(20), nullable=True, server_default="ok"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("triggered_by", sa.String(20), nullable=True, server_default="manual"),
            sa.Column("includes_media", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("destinations_json", JSONB, nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "health_samples" not in tables:
        op.create_table(
            "health_samples",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("service_key", sa.String(40), nullable=True),
            sa.Column("status", sa.String(12), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("detail", sa.String(300), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_health_samples_service_key", "health_samples", ["service_key"])
        op.create_index("ix_health_samples_checked_at", "health_samples", ["checked_at"])


def downgrade() -> None:
    for t in ("health_samples", "backup_records", "backup_settings"):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
