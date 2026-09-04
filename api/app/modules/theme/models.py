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
    accent_color: Mapped[str] = mapped_column(String(9), default="#FFC400")
    text_color: Mapped[str] = mapped_column(String(9), default="#111827")
    bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")

    # botões (estilo Customizer do WordPress / WooCommerce)
    button_bg_color: Mapped[str] = mapped_column(String(9), default="#111111")
    button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")
    button_hover_color: Mapped[str] = mapped_column(String(9), default="#DC2626")
    # borda do botão "Comprar" — igual ao fundo por padrão (some visualmente);
    # some visualmente até o lojista escolher uma cor diferente do fundo.
    button_border_color: Mapped[str] = mapped_column(
        String(9), default="#111111", server_default="#111111", nullable=False
    )

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
    # carrossel: quando ligado, roda as 3 mensagens; senão mostra só a 1ª
    top_bar_carousel: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # texto centralizado na tarja (senão fica à esquerda, WhatsApp à direita)
    top_bar_centered: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    top_bar_message_2: Mapped[str | None] = mapped_column(String(240))
    top_bar_message_3: Mapped[str | None] = mapped_column(String(240))
    top_bar_bg_color: Mapped[str] = mapped_column(
        String(9), default="#111111", server_default="#111111", nullable=False
    )
    top_bar_text_color: Mapped[str] = mapped_column(
        String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False
    )

    # Texto logo abaixo do logo do rodapé (herda a cor de texto do rodapé)
    footer_note_text: Mapped[str] = mapped_column(
        String(500),
        default=(
            "Preços e condições de pagamento exclusivos para compras via internet. "
            "Endereço comercial disponível na página Fale conosco."
        ),
        server_default=(
            "Preços e condições de pagamento exclusivos para compras via internet. "
            "Endereço comercial disponível na página Fale conosco."
        ),
        nullable=False,
    )

    # Tarja de copyright no rodapé de tudo (variáveis: {ano} {loja} {cnpj})
    footer_copyright_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    footer_copyright_text: Mapped[str] = mapped_column(
        String(400),
        default="© {ano} {loja} — CNPJ {cnpj}. Todos os Direitos Reservados.",
        server_default="© {ano} {loja} — CNPJ {cnpj}. Todos os Direitos Reservados.",
        nullable=False,
    )
    footer_copyright_bg_color: Mapped[str] = mapped_column(
        String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False
    )
    footer_copyright_text_color: Mapped[str] = mapped_column(
        String(9), default="#6B7280", server_default="#6B7280", nullable=False
    )

    # Redes sociais no rodapé (URL vem de StoreSettings.social_json)
    footer_social_instagram_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    footer_social_facebook_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    footer_social_tiktok_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    footer_social_youtube_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

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
    # atalhos de filtro também na home (senão só nas telas de categoria)
    filters_on_home: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    # bloco "Você também pode gostar" na página do produto (abaixo das avaliações)
    pdp_related_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Modelo do checkout (menu "Checkout" no admin)
    checkout_email_first: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    # exigir o aceite "Li e concordo com a política de vendas / privacidade"
    checkout_require_terms: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    checkout_container_width_px: Mapped[int] = mapped_column(Integer, default=1100, server_default="1100", nullable=False)
    checkout_items_layout: Mapped[str] = mapped_column(String(12), default="with_thumb", server_default="with_thumb", nullable=False)  # with_thumb | simple
    checkout_show_coupon: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_allow_qty_change: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_footer_note: Mapped[str | None] = mapped_column(String(240))
    checkout_animated_card: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    # Ícones ao lado de cada forma de pagamento (PIX / cartão / boleto)
    checkout_payment_icons_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    # Linha do tempo das etapas (1 2 3 4) no topo do checkout
    checkout_steps_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_show_review: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    checkout_review_position: Mapped[str] = mapped_column(String(8), default="side", server_default="side", nullable=False)  # side | top
    # Caixa "Observações do pedido (opcional)" no checkout — desligada por padrão
    checkout_order_notes_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
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
    checkout_button_color: Mapped[str] = mapped_column(String(9), default="#FFC400", server_default="#111111", nullable=False)
    checkout_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    # borda do botão "Finalizar" — igual ao fundo por padrão (some visualmente)
    checkout_button_border_color: Mapped[str] = mapped_column(
        String(9), default="#FFC400", server_default="#FFC400", nullable=False
    )
    checkout_accent_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_footer_bg_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    checkout_footer_text_color: Mapped[str] = mapped_column(String(9), default="#E5E7EB", server_default="#E5E7EB", nullable=False)
    # botões "Avançar"/"Calcular frete" das etapas
    checkout_step_button_color: Mapped[str] = mapped_column(String(9), default="#FFC400", server_default="#111111", nullable=False)
    checkout_step_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    # borda dos botões de etapa — igual ao fundo por padrão (some visualmente)
    checkout_step_button_border_color: Mapped[str] = mapped_column(
        String(9), default="#FFC400", server_default="#FFC400", nullable=False
    )
    # bolinha da etapa ativa (1,2,3,4) na linha do tempo
    checkout_step_active_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    checkout_step_active_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)

    # Newsletter (bloco de captura na home) — menu "Newsletter" no admin
    newsletter_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    newsletter_title: Mapped[str] = mapped_column(String(120), default="Receba novidades e ofertas", server_default="Receba novidades e ofertas", nullable=False)
    newsletter_subtitle: Mapped[str] = mapped_column(String(240), default="Cadastre seu e-mail e fique por dentro dos lançamentos.", server_default="Cadastre seu e-mail e fique por dentro dos lançamentos.", nullable=False)
    newsletter_bg_color: Mapped[str] = mapped_column(String(9), default="#F5F5F5", server_default="#F5F5F5", nullable=False)
    newsletter_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    newsletter_button_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    newsletter_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)

    # Popup de captura de leads (link "Cadastre-se e ganhe X% OFF")
    lead_popup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    # Link "Cadastre-se e ganhe..." na página do produto (abre o mesmo popup ao clicar)
    lead_popup_pdp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    lead_capture_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    lead_popup_title: Mapped[str] = mapped_column(String(160), default="Cadastre-se para 10% OFF na primeira compra", server_default="Cadastre-se para 10% OFF na primeira compra", nullable=False)
    lead_popup_subtitle: Mapped[str] = mapped_column(String(280), default="Receba promoções e conteúdos exclusivos.", server_default="Receba promoções e conteúdos exclusivos.", nullable=False)
    lead_popup_coupon_code: Mapped[str | None] = mapped_column(String(60))
    lead_popup_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    lead_popup_text_color: Mapped[str] = mapped_column(String(9), default="#111827", server_default="#111827", nullable=False)
    lead_popup_button_color: Mapped[str] = mapped_column(String(9), default="#F5B301", server_default="#F5B301", nullable=False)
    lead_popup_button_text_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    # logo próprio do popup (opcional). Vazio + show_logo=true => usa o logo da loja.
    lead_popup_logo_key: Mapped[str | None] = mapped_column(String(300))
    lead_popup_show_logo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    # Selo de desconto (-XX%) calculado do preço "de" x preço promocional
    discount_badge_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Raio das bordas dos botões (px) — CSS var --radius-btn
    button_radius_px: Mapped[int] = mapped_column(
        Integer, default=12, server_default="12", nullable=False
    )
    # Raio das caixas de variação (numeração/cor na PDP) — CSS var --radius-var
    variation_radius_px: Mapped[int] = mapped_column(
        Integer, default=12, server_default="12", nullable=False
    )

    # PDP — bloco de reassurance abaixo do botão de compra
    pdp_reassurance_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    pdp_reassurance_items: Mapped[list] = mapped_column(
        JSONB,
        default=lambda: [
            "🔄 Troca fácil em até 30 dias",
            "🔒 Site 100% seguro — pagamento criptografado",
            "📦 Enviamos para todo o Brasil pelos Correios",
        ],
        server_default=(
            '["🔄 Troca fácil em até 30 dias", '
            '"🔒 Site 100% seguro — pagamento criptografado", '
            '"📦 Enviamos para todo o Brasil pelos Correios"]'
        ),
        nullable=False,
    )

    # Botão "Calcular frete" na PDP — cores próprias
    freight_button_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    freight_button_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    freight_button_hover_color: Mapped[str] = mapped_column(String(9), default="#333333", server_default="#333333", nullable=False)
    freight_button_border_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    freight_button_radius_px: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)

    # Selo de promoção (-XX%) — cor de fundo e texto
    promo_badge_bg_color: Mapped[str] = mapped_column(String(9), default="#DC2626", server_default="#DC2626", nullable=False)
    promo_badge_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    promo_badge_border_color: Mapped[str] = mapped_column(String(9), default="#DC2626", server_default="#DC2626", nullable=False)
    promo_badge_radius_px: Mapped[int] = mapped_column(Integer, default=6, server_default="6", nullable=False)
    # Exibir o selo (-XX%) por superfície (só quando discount_badge_enabled está ligado)
    promo_badge_card_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    promo_badge_pdp_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    # ---- Carrinho (menu "Carrinho" na Aparência) ----
    # Botão "Finalizar compra"
    cart_checkout_btn_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_checkout_btn_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    cart_checkout_btn_hover_color: Mapped[str] = mapped_column(String(9), default="#333333", server_default="#333333", nullable=False)
    cart_checkout_btn_border_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_checkout_btn_radius_px: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)
    # Botão "Calcular" (frete) no carrinho
    cart_freight_btn_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_freight_btn_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    cart_freight_btn_hover_color: Mapped[str] = mapped_column(String(9), default="#333333", server_default="#333333", nullable=False)
    cart_freight_btn_border_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_freight_btn_radius_px: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)
    # Caixinhas de quantidade (−/valor/+) no carrinho
    cart_qty_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    cart_qty_text_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_qty_radius_px: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)
    # Botão "Aplicar" do cupom no carrinho
    cart_coupon_btn_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    cart_coupon_btn_text_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_coupon_btn_hover_color: Mapped[str] = mapped_column(String(9), default="#F3F3F3", server_default="#F3F3F3", nullable=False)
    cart_coupon_btn_border_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_coupon_btn_radius_px: Mapped[int] = mapped_column(Integer, default=12, server_default="12", nullable=False)

    # Bolinha de contagem na sacola (cabeçalho)
    cart_badge_bg_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    cart_badge_text_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)

    # PDP / cards
    pdp_qty_selector_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    wishlist_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    # Botão de favoritar (coração) na página do produto
    pdp_wishlist_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    pdp_wishlist_border_color: Mapped[str] = mapped_column(String(9), default="#DC2626", server_default="#DC2626", nullable=False)
    pdp_wishlist_icon_color: Mapped[str] = mapped_column(String(9), default="#DC2626", server_default="#DC2626", nullable=False)
    card_hover_zoom_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    card_buy_button_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    card_buy_button_label: Mapped[str] = mapped_column(String(40), default="COMPRAR", server_default="COMPRAR", nullable=False)
    # Popup "Tabela de medidas" na PDP
    size_chart_bg_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    size_chart_header_bg_color: Mapped[str] = mapped_column(String(9), default="#FFC400", server_default="#FFC400", nullable=False)
    size_chart_header_text_color: Mapped[str] = mapped_column(String(9), default="#111111", server_default="#111111", nullable=False)
    size_chart_text_color: Mapped[str] = mapped_column(String(9), default="#374151", server_default="#374151", nullable=False)

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
