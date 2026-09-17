"""Domínios próprios apontados pro proxy reverso (aaPanel/LiteSpeed) + SSL."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, TimestampMixin, UUIDPKMixin

# ciclo de vida de um domínio:
#   pending -> awaiting_nameservers (só quando a Cloudflare cria a zona e
#              espera o usuário trocar os nameservers no registrador)
#           -> dns_pending (DNS manual ainda não propagou / zona já ativa mas
#              vhost/SSL ainda não)
#           -> provisioning -> active
#                            -> failed (qualquer etapa)
STATUS_PENDING = "pending"
STATUS_AWAITING_NAMESERVERS = "awaiting_nameservers"
STATUS_DNS_PENDING = "dns_pending"
STATUS_PROVISIONING = "provisioning"
STATUS_ACTIVE = "active"
STATUS_FAILED = "failed"


class Domain(UUIDPKMixin, TimestampMixin, Base):
    """Domínio raiz cadastrado (`admin.` e `api.` são derivados, não linhas próprias)."""

    __tablename__ = "domains"

    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING)
    dns_managed_by_cloudflare: Mapped[bool] = mapped_column(Boolean, default=False)
    ssl_status: Mapped[str] = mapped_column(String(20), default="none")
    last_error: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # zona Cloudflare — só preenchido quando a automação cria/encontra a zona
    cloudflare_zone_id: Mapped[str | None] = mapped_column(String(64))
    cloudflare_nameservers: Mapped[list | None] = mapped_column(JSONB)
    # marcado quando a rotina de checagem confirma que os nameservers
    # propagaram (zona Cloudflare "active") — a partir daí o scheduler para
    # de checar este domínio; só volta a checar se o domínio for removido e
    # cadastrado de novo (linha nova, campo nasce None de novo).
    dns_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # quais tipos de página o admin marcou pra cache agressivo na Cloudflare
    # (chaves de CACHE_PAGE_DEFS, em cache_rules.py) — carrinho/checkout/conta/
    # favoritos/recuperação de senha NUNCA entram aqui, são bypass sempre,
    # não é uma opção do usuário.
    cache_pages: Mapped[list | None] = mapped_column(JSONB)
    cache_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
