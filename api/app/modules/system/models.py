"""Modelos do módulo `system`: configuração de backup, registro de backups e
amostras de saúde (histórico das barrinhas tipo Uptime Kuma)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin


class BackupSettings(Base):
    """Configuração de backup. Linha única (id=1)."""

    __tablename__ = "backup_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    auto_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    frequency: Mapped[str] = mapped_column(String(12), default="diario", server_default="diario", nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, default=3, server_default="3", nullable=False)
    keep: Mapped[int] = mapped_column(SmallInteger, default=7, server_default="7", nullable=False)
    include_media: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    # cópia redundante para uma pasta local/rede montada no servidor
    folder_path: Mapped[str | None] = mapped_column(String(500))
    # cópia por SFTP: {enabled, host, port, user, password, key_path, remote_dir}
    sftp_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    # cópia para o Google Drive: {enabled, folder_id, service_account_json_path, account_email}
    gdrive_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupRecord(UUIDPKMixin, Base):
    __tablename__ = "backup_records"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | error | running
    error_message: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual")  # manual | auto | import | pre-restore
    includes_media: Mapped[bool] = mapped_column(Boolean, default=False)
    destinations_json: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthSample(UUIDPKMixin, Base):
    """Uma verificação de um serviço num instante — alimenta as barrinhas."""

    __tablename__ = "health_samples"

    service_key: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(12))  # ok | degraded | down
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(String(300))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
