"""Modelos do módulo `theme` — tema visual (singleton) e páginas institucionais."""
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
    false,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models_base import Base, UUIDPKMixin


class ThemeSettings(Base):
    """Tema visual. Linha única (id=1). Refletido no frontend por SSR, sem rebuild."""

    __tablename__ = "theme_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    primary_color: Mapped[str] = mapped_column(String(9), default="#111111")
    secondary_color: Mapped[str] = mapped_column(String(9), default="#4B5563")
    accent_color: Mapped[str] = mapped_column(String(9), default="#DC2626")
    text_color: Mapped[str] = mapped_column(String(9), default="#111827")
    bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")

    # botões (estilo Customizer do WordPress / WooCommerce)
    button_bg_color: Mapped[str] = mapped_column(String(9), default="#111111")
    button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")
    button_hover_color: Mapped[str] = mapped_column(String(9), default="#DC2626")

    # caixas de variação (numeração/cor na PDP) + botão "calcular frete"
    variation_bg_color: Mapped[str] = mapped_column(String(9), default="#FDE047", server_default="#FDE047", nullable=False)
    variation_text_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    variation_border_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)

    # menu superior (header)
    header_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")
    header_text_color: Mapped[str] = mapped_column(String(9), default="#111827")
    header_max_width_px: Mapped[int] = mapped_column(Integer, default=1280)

    # menu inferior (footer / rodapé)
    footer_bg_color: Mapped[str] = mapped_column(String(9), default="#111827")
    footer_text_color: Mapped[str] = mapped_column(String(9), default="#E5E7EB")

    logo_key: Mapped[str | None] = mapped_column(String(300))
    logo_mobile_key: Mapped[str | None] = mapped_column(String(300))
    favicon_key: Mapped[str | None] = mapped_column(String(300))
    font_family: Mapped[str] = mapped_column(String(120), default="Inter, system-ui, sans-serif")
    free_shipping_threshold_cents: Mapped[int | None] = mapped_column(Integer)
    whatsapp_number: Mapped[str | None] = mapped_column(String(32))
    top_bar_message: Mapped[str | None] = mapped_column(String(240))
    top_bar_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Banner principal (hero) da home
    hero_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    hero_mode: Mapped[str] = mapped_column(String(12), default="carousel", server_default="carousel", nullable=False)  # carousel | static
    hero_autoplay_seconds: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)

    # Selos do rodapé (Formas de Pagamento / Entrega / Loja Segura)
    footer_seals_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    footer_seals_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    # Comportamento: ir para /carrinho após adicionar (senão fica na PDP)
    cart_redirect_after_add: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    # Modelo do checkout (menu "Checkout" no admin)
    checkout_email_first: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    checkout_container_width_px: Mapped[int] = mapped_column(Integer, default=1100, server_default="1100", nullable=False)
    checkout_items_layout: Mapped[str] = mapped_column(String(12), default="with_thumb", server_default="with_thumb", nullable=False)  # with_thumb | simple
    checkout_show_coupon: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_allow_qty_change: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_footer_note: Mapped[str | None] = mapped_column(String(240))
    # cores próprias do checkout (menu "Checkout")
    checkout_bg_color: Mapped[str] = mapped_column(String(9), default="#F7F7F7", server_default="#F7F7F7", nullable=False)
    checkout_header_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    checkout_header_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    checkout_button_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    checkout_accent_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_footer_bg_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    checkout_footer_text_color: Mapped[str] = mapped_column(String(9), default="#E5E7EB", server_default="#E5E7EB", nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class Page(UUIDPKMixin, Base):
    """Páginas institucionais do rodapé (Quem Somos, Políticas, FAQ...)."""

    __tablename__ = "pages"

    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    seo_title: Mapped[str | None] = mapped_column(String(200))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
