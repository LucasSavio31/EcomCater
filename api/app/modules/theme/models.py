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
    # Mini-carrinho lateral: abre ao adicionar (tem precedência sobre o redirect)
    mini_cart_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Filtros da vitrine (menu "Filtros" no admin)
    filter_size_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    filter_price_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    filter_category_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    filter_color_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    filter_material_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    # Modelo do checkout (menu "Checkout" no admin)
    checkout_email_first: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    checkout_container_width_px: Mapped[int] = mapped_column(Integer, default=1100, server_default="1100", nullable=False)
    checkout_items_layout: Mapped[str] = mapped_column(String(12), default="with_thumb", server_default="with_thumb", nullable=False)  # with_thumb | simple
    checkout_show_coupon: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_allow_qty_change: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_footer_note: Mapped[str | None] = mapped_column(String(240))
    checkout_animated_card: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_show_review: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_review_position: Mapped[str] = mapped_column(String(8), default="side", server_default="side", nullable=False)  # side | top
    checkout_orderbump_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    checkout_orderbump_product_id: Mapped[str | None] = mapped_column(String(200))  # legado (1 slug)
    # Order bump: lista de ids/slugs de produtos oferecidos no checkout
    checkout_orderbump_product_ids: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    # cores próprias do checkout (menu "Checkout")
    checkout_bg_color: Mapped[str] = mapped_column(String(9), default="#F7F7F7", server_default="#F7F7F7", nullable=False)
    checkout_header_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    checkout_header_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    checkout_button_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    checkout_accent_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_footer_bg_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    checkout_footer_text_color: Mapped[str] = mapped_column(String(9), default="#E5E7EB", server_default="#E5E7EB", nullable=False)

    # Newsletter (bloco de captura na home) — menu "Newsletter" no admin
    newsletter_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    newsletter_title: Mapped[str] = mapped_column(String(120), default="Receba novidades e ofertas", server_default="Receba novidades e ofertas", nullable=False)
    newsletter_subtitle: Mapped[str] = mapped_column(String(240), default="Cadastre seu e-mail e fique por dentro dos lançamentos.", server_default="Cadastre seu e-mail e fique por dentro dos lançamentos.", nullable=False)
    newsletter_bg_color: Mapped[str] = mapped_column(String(9), default="#F5F5F5", server_default="#F5F5F5", nullable=False)
    newsletter_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    newsletter_button_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    newsletter_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)

    # Selo de desconto (-XX%) calculado do preço "de" x preço promocional
    discount_badge_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Raio das bordas dos botões (px) — CSS var --radius-btn
    button_radius_px: Mapped[int] = mapped_column(
        Integer, default=12, server_default="12", nullable=False
    )

    # Aviso de cookies de terceiros
    cookie_consent_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    cookie_consent_text: Mapped[str] = mapped_column(
        String(400),
        default="Usamos cookies para melhorar sua experiência. Ao continuar, você concorda com a nossa política de privacidade.",
        server_default="Usamos cookies para melhorar sua experiência. Ao continuar, você concorda com a nossa política de privacidade.",
        nullable=False,
    )

    # Identidade visual dos e-mails transacionais
    email_header_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    email_header_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    email_body_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    email_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    email_button_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    email_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    email_footer_text: Mapped[str] = mapped_column(
        String(300), default="", server_default="", nullable=False
    )

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
