"""Modelos do módulo `admin`: usuários administrativos, refresh tokens (cliente +
admin), registro de módulos e configurações gerais da loja."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

# papéis simples (decisão da fase 0)
ADMIN_ROLES = ("super_admin", "admin", "staff")


class AdminUser(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(20), default="staff")
    permissions_json: Mapped[dict] = mapped_column(JSONB, default=dict)  # reservado p/ futuro
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 2FA (TOTP / Google Authenticator)
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    recovery_codes_json: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    __table_args__ = (
        CheckConstraint("role in ('super_admin','admin','staff')", name="role_valid"),
    )


class AuthRefreshToken(UUIDPKMixin, Base):
    """Refresh tokens de clientes e admins (escopo em `subject_type`)."""

    __tablename__ = "auth_refresh_tokens"

    subject_type: Mapped[str] = mapped_column(String(10))  # customer | admin
    subject_id: Mapped[str] = mapped_column(String(36), index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("subject_type in ('customer','admin')", name="subject_type_valid"),
    )


class ModuleRow(Base):
    """Habilitação + config por módulo (editável pelo admin)."""

    __tablename__ = "modules"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class StoreSettings(Base):
    """Configurações gerais não-tema. Linha única (id=1)."""

    __tablename__ = "store_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    store_name: Mapped[str] = mapped_column(String(160), default="Minha Loja")
    legal_name: Mapped[str | None] = mapped_column(String(200))
    cnpj: Mapped[str | None] = mapped_column(String(18))
    address_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    social_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_whatsapp: Mapped[str | None] = mapped_column(String(32))
    payment_flags_json: Mapped[list] = mapped_column(JSONB, default=list)
    free_shipping_threshold_cents: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class SmtpSettings(Base):
    """Config de SMTP. Linha única (id=1). Sobrescreve o fallback do .env."""

    __tablename__ = "smtp_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    host: Mapped[str | None] = mapped_column(String(200))
    port: Mapped[int | None] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(200))
    password_enc: Mapped[str | None] = mapped_column(Text)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    from_email: Mapped[str | None] = mapped_column(String(200))
    from_name: Mapped[str | None] = mapped_column(String(160))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailLog(UUIDPKMixin, Base):
    __tablename__ = "email_log"

    to_email: Mapped[str] = mapped_column(String(200), index=True)
    template: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10))  # sent | failed
    error: Mapped[str | None] = mapped_column(Text)
    order_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
