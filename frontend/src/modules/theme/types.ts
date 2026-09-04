/** Resposta de `GET /api/theme` (linha única `theme_settings`, com fallback no back). */
export interface ThemeSettings {
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  text_color: string;
  bg_color: string;
  /** Botões (estilo Customizer do WooCommerce). */
  button_bg_color: string;
  button_text_color: string;
  button_hover_color: string;
  /** Borda do botão "Comprar" — igual ao fundo por padrão (some visualmente). */
  button_border_color: string;
  /** Caixas de variação (PDP) + botão "calcular frete". */
  variation_bg_color: string;
  variation_text_color: string;
  variation_border_color: string;
  /** Menu superior (header). */
  header_bg_color: string;
  header_text_color: string;
  header_max_width_px: number;
  /** Rodapé (footer). */
  footer_bg_color: string;
  footer_text_color: string;
  font_family: string;
  logo_key?: string | null;
  logo_mobile_key?: string | null;
  logo_url?: string | null;
  favicon_key?: string | null;
  favicon_url?: string | null;
  /** Dados da loja (rodapé / copyright). */
  store_name?: string | null;
  legal_name?: string | null;
  cnpj?: string | null;
  /** Texto abaixo do logo do rodapé (herda a cor de texto do rodapé). */
  footer_note_text: string;
  /** Tarja de copyright no rodapé de tudo. Vars: {ano} {loja} {cnpj}. */
  footer_copyright_enabled: boolean;
  footer_copyright_text: string;
  footer_copyright_bg_color: string;
  footer_copyright_text_color: string;
  /** Redes sociais no rodapé (URL vem de social_json). */
  footer_social_instagram_enabled: boolean;
  footer_social_facebook_enabled: boolean;
  footer_social_tiktok_enabled: boolean;
  footer_social_youtube_enabled: boolean;
  social_json?: Record<string, string> | null;
  free_shipping_threshold_cents?: number | null;
  whatsapp_number?: string | null;
  top_bar_message?: string | null;
  top_bar_enabled: boolean;
  /** Barra superior em carrossel: roda as 3 mensagens; senão mostra só a 1ª. */
  top_bar_carousel: boolean;
  top_bar_centered: boolean;
  top_bar_message_2?: string | null;
  top_bar_message_3?: string | null;
  top_bar_bg_color: string;
  top_bar_text_color: string;
  /** Banner principal (hero) da home. */
  hero_enabled: boolean;
  hero_mode: 'carousel' | 'static';
  hero_autoplay_seconds: number;
  /** Selos do rodapé. */
  footer_seals_enabled: boolean;
  footer_seals_json: FooterSeals;
  /** Após adicionar ao carrinho: true = vai para /carrinho, false = fica na PDP. */
  cart_redirect_after_add: boolean;
  /** Mini-carrinho lateral ao adicionar (tem precedência sobre o redirect). */
  mini_cart_enabled: boolean;
  /** Filtros da vitrine (menu "Filtros" no admin). */
  filter_size_enabled: boolean;
  filter_color_enabled: boolean;
  filter_material_enabled: boolean;
  filter_price_enabled: boolean;
  filter_category_enabled: boolean;
  filters_on_home: boolean;
  pdp_related_enabled: boolean;
  /** Modelo do checkout (menu "Checkout" no admin). */
  checkout_email_first: boolean;
  checkout_require_terms: boolean;
  checkout_container_width_px: number;
  checkout_items_layout: 'with_thumb' | 'simple';
  checkout_show_coupon: boolean;
  checkout_allow_qty_change: boolean;
  checkout_footer_note: string | null;
  checkout_animated_card: boolean;
  checkout_payment_icons_enabled: boolean;
  checkout_steps_enabled: boolean;
  checkout_show_review: boolean;
  checkout_review_position: 'side' | 'top';
  checkout_order_notes_enabled: boolean;
  checkout_orderbump_enabled: boolean;
  checkout_orderbump_product_id: string | null;
  checkout_orderbump_product_ids: string[];
  /** Cores próprias do checkout. */
  checkout_bg_color: string;
  checkout_header_bg_color: string;
  checkout_header_text_color: string;
  checkout_button_color: string;
  checkout_button_text_color: string;
  /** Borda do botão "Finalizar" — igual ao fundo por padrão (some visualmente). */
  checkout_button_border_color: string;
  checkout_accent_color: string;
  checkout_footer_bg_color: string;
  checkout_footer_text_color: string;
  checkout_step_button_color: string;
  checkout_step_button_text_color: string;
  /** Borda dos botões de etapa — igual ao fundo por padrão (some visualmente). */
  checkout_step_button_border_color: string;
  checkout_step_active_bg_color: string;
  checkout_step_active_text_color: string;
  /** Bloco de newsletter na home (menu "Newsletter"). */
  newsletter_enabled: boolean;
  newsletter_title: string;
  newsletter_subtitle: string;
  newsletter_bg_color: string;
  newsletter_text_color: string;
  newsletter_button_color: string;
  newsletter_button_text_color: string;
  discount_badge_enabled: boolean;
  lead_popup_enabled: boolean;
  lead_popup_pdp_enabled: boolean;
  lead_capture_enabled: boolean;
  lead_popup_title: string;
  lead_popup_subtitle: string;
  lead_popup_coupon_code: string | null;
  lead_popup_bg_color: string;
  lead_popup_text_color: string;
  lead_popup_button_color: string;
  lead_popup_button_text_color: string;
  lead_popup_logo_url?: string | null;
  lead_popup_show_logo: boolean;
  button_radius_px: number;
  variation_radius_px: number;
  pdp_reassurance_enabled: boolean;
  pdp_reassurance_items: string[];
  freight_button_bg_color: string;
  freight_button_text_color: string;
  freight_button_hover_color: string;
  freight_button_border_color: string;
  freight_button_radius_px: number;
  promo_badge_bg_color: string;
  promo_badge_text_color: string;
  promo_badge_border_color: string;
  promo_badge_radius_px: number;
  promo_badge_card_enabled: boolean;
  promo_badge_pdp_enabled: boolean;
  cart_checkout_btn_bg_color: string;
  cart_checkout_btn_text_color: string;
  cart_checkout_btn_hover_color: string;
  cart_checkout_btn_border_color: string;
  cart_checkout_btn_radius_px: number;
  cart_freight_btn_bg_color: string;
  cart_freight_btn_text_color: string;
  cart_freight_btn_hover_color: string;
  cart_freight_btn_border_color: string;
  cart_freight_btn_radius_px: number;
  cart_qty_bg_color: string;
  cart_qty_text_color: string;
  cart_qty_radius_px: number;
  cart_coupon_btn_bg_color: string;
  cart_coupon_btn_text_color: string;
  cart_coupon_btn_hover_color: string;
  cart_coupon_btn_border_color: string;
  cart_coupon_btn_radius_px: number;
  cart_badge_bg_color: string;
  cart_badge_text_color: string;
  pdp_qty_selector_enabled: boolean;
  size_chart_bg_color: string;
  size_chart_header_bg_color: string;
  size_chart_header_text_color: string;
  size_chart_text_color: string;
  wishlist_enabled: boolean;
  pdp_wishlist_bg_color: string;
  pdp_wishlist_border_color: string;
  pdp_wishlist_icon_color: string;
  card_hover_zoom_enabled: boolean;
  card_buy_button_enabled: boolean;
  card_buy_button_label: string;
  cookie_consent_enabled: boolean;
  cookie_consent_text: string;
  email_header_bg_color: string;
  email_header_text_color: string;
  email_body_bg_color: string;
  email_text_color: string;
  email_button_color: string;
  email_button_text_color: string;
  email_footer_text: string;
  updated_at?: string | null;
}

export interface FooterSealColumn {
  title: string;
  text: string;
  badges: string[];
  /** chaves das imagens enviadas no admin */
  images: string[];
  /** URLs prontas das imagens enviadas */
  image_urls: string[];
}

export interface FooterSeals {
  payment: FooterSealColumn;
  shipping: FooterSealColumn;
  security: FooterSealColumn;
}

const emptyCol = (title: string, badges: string[], text = ''): FooterSealColumn => ({
  title,
  text,
  badges,
  images: [],
  image_urls: [],
});

const DEFAULT_SEALS: FooterSeals = {
  payment: emptyCol('Formas de Pagamento', ['Pix', 'Boleto', 'Visa', 'Mastercard', 'Amex', 'Elo', 'Hipercard']),
  shipping: emptyCol('Formas de Entrega', ['Correios']),
  security: emptyCol('Loja Segura', ['SSL'], 'Site 100% seguro, com criptografia e certificado SSL.'),
};

/** Paleta neutra — usada quando a API está fora do ar (build, incidente). */
export const NEUTRAL_THEME: ThemeSettings = {
  primary_color: '#111111',
  secondary_color: '#4B5563',
  accent_color: '#FFC400',
  text_color: '#111827',
  bg_color: '#FFFFFF',
  button_bg_color: '#111111',
  button_text_color: '#FFFFFF',
  button_hover_color: '#DC2626',
  button_border_color: '#111111',
  variation_bg_color: '#FDE047',
  variation_text_color: '#111111',
  variation_border_color: '#111111',
  header_bg_color: '#FFFFFF',
  header_text_color: '#111827',
  header_max_width_px: 1280,
  footer_bg_color: '#111827',
  footer_text_color: '#E5E7EB',
  font_family: 'Inter, system-ui, sans-serif',
  logo_url: null,
  favicon_url: null,
  store_name: null,
  legal_name: null,
  cnpj: null,
  footer_note_text:
    'Preços e condições de pagamento exclusivos para compras via internet. Endereço comercial disponível na página Fale conosco.',
  footer_copyright_enabled: true,
  footer_copyright_text: '© {ano} {loja} — CNPJ {cnpj}. Todos os Direitos Reservados.',
  footer_copyright_bg_color: '#FFFFFF',
  footer_copyright_text_color: '#6B7280',
  footer_social_instagram_enabled: false,
  footer_social_facebook_enabled: false,
  footer_social_tiktok_enabled: false,
  footer_social_youtube_enabled: false,
  social_json: null,
  top_bar_enabled: false,
  top_bar_message: null,
  top_bar_carousel: false,
  top_bar_centered: false,
  top_bar_message_2: null,
  top_bar_message_3: null,
  top_bar_bg_color: '#111111',
  top_bar_text_color: '#FFFFFF',
  hero_enabled: true,
  hero_mode: 'carousel',
  hero_autoplay_seconds: 5,
  footer_seals_enabled: true,
  footer_seals_json: DEFAULT_SEALS,
  cart_redirect_after_add: false,
  mini_cart_enabled: true,
  filter_size_enabled: true,
  filter_color_enabled: true,
  filter_material_enabled: true,
  filter_price_enabled: true,
  filter_category_enabled: true,
  filters_on_home: true,
  pdp_related_enabled: true,
  checkout_email_first: false,
  checkout_require_terms: true,
  checkout_container_width_px: 1100,
  checkout_items_layout: 'with_thumb',
  checkout_show_coupon: true,
  checkout_allow_qty_change: true,
  checkout_footer_note: null,
  checkout_animated_card: true,
  checkout_payment_icons_enabled: true,
  checkout_steps_enabled: true,
  checkout_show_review: true,
  checkout_review_position: 'side',
  checkout_order_notes_enabled: false,
  checkout_orderbump_enabled: false,
  checkout_orderbump_product_id: null,
  checkout_orderbump_product_ids: [],
  checkout_bg_color: '#F7F7F7',
  checkout_header_bg_color: '#FFFFFF',
  checkout_header_text_color: '#111827',
  checkout_button_color: '#FFC400',
  checkout_button_text_color: '#FFFFFF',
  checkout_button_border_color: '#FFC400',
  checkout_accent_color: '#111111',
  checkout_footer_bg_color: '#111827',
  checkout_footer_text_color: '#E5E7EB',
  checkout_step_button_color: '#FFC400',
  checkout_step_button_text_color: '#FFFFFF',
  checkout_step_button_border_color: '#FFC400',
  checkout_step_active_bg_color: '#111111',
  checkout_step_active_text_color: '#FFFFFF',
  newsletter_enabled: true,
  newsletter_title: 'Receba novidades e ofertas',
  newsletter_subtitle: 'Cadastre seu e-mail e fique por dentro dos lançamentos.',
  newsletter_bg_color: '#F5F5F5',
  newsletter_text_color: '#111827',
  newsletter_button_color: '#111111',
  newsletter_button_text_color: '#FFFFFF',
  discount_badge_enabled: true,
  lead_popup_enabled: false,
  lead_popup_pdp_enabled: false,
  lead_capture_enabled: true,
  lead_popup_title: 'Cadastre-se para 10% OFF na primeira compra',
  lead_popup_subtitle: 'Receba promoções e conteúdos exclusivos.',
  lead_popup_coupon_code: null,
  lead_popup_bg_color: '#FFFFFF',
  lead_popup_text_color: '#111827',
  lead_popup_button_color: '#F5B301',
  lead_popup_button_text_color: '#111111',
  lead_popup_logo_url: null,
  lead_popup_show_logo: true,
  button_radius_px: 12,
  variation_radius_px: 12,
  pdp_reassurance_enabled: true,
  pdp_reassurance_items: [
    '🔄 Troca fácil em até 30 dias',
    '🔒 Site 100% seguro — pagamento criptografado',
    '📦 Enviamos para todo o Brasil pelos Correios',
  ],
  freight_button_bg_color: '#111111',
  freight_button_text_color: '#FFFFFF',
  freight_button_hover_color: '#333333',
  freight_button_border_color: '#111111',
  freight_button_radius_px: 12,
  promo_badge_bg_color: '#DC2626',
  promo_badge_text_color: '#FFFFFF',
  promo_badge_border_color: '#DC2626',
  promo_badge_radius_px: 6,
  promo_badge_card_enabled: true,
  promo_badge_pdp_enabled: true,
  cart_checkout_btn_bg_color: '#111111',
  cart_checkout_btn_text_color: '#FFFFFF',
  cart_checkout_btn_hover_color: '#333333',
  cart_checkout_btn_border_color: '#111111',
  cart_checkout_btn_radius_px: 12,
  cart_freight_btn_bg_color: '#111111',
  cart_freight_btn_text_color: '#FFFFFF',
  cart_freight_btn_hover_color: '#333333',
  cart_freight_btn_border_color: '#111111',
  cart_freight_btn_radius_px: 12,
  cart_qty_bg_color: '#FFFFFF',
  cart_qty_text_color: '#111111',
  cart_qty_radius_px: 12,
  cart_coupon_btn_bg_color: '#FFFFFF',
  cart_coupon_btn_text_color: '#111111',
  cart_coupon_btn_hover_color: '#F3F3F3',
  cart_coupon_btn_border_color: '#111111',
  cart_coupon_btn_radius_px: 12,
  cart_badge_bg_color: '#111111',
  cart_badge_text_color: '#FFFFFF',
  pdp_qty_selector_enabled: true,
  size_chart_bg_color: '#FFFFFF',
  size_chart_header_bg_color: '#FFC400',
  size_chart_header_text_color: '#111111',
  size_chart_text_color: '#374151',
  wishlist_enabled: true,
  pdp_wishlist_bg_color: '#FFFFFF',
  pdp_wishlist_border_color: '#DC2626',
  pdp_wishlist_icon_color: '#DC2626',
  card_hover_zoom_enabled: true,
  card_buy_button_enabled: false,
  card_buy_button_label: 'COMPRAR',
  cookie_consent_enabled: false,
  cookie_consent_text:
    'Usamos cookies para melhorar sua experiência. Ao continuar, você concorda com a nossa política de privacidade.',
  email_header_bg_color: '#111111',
  email_header_text_color: '#FFFFFF',
  email_body_bg_color: '#FFFFFF',
  email_text_color: '#111827',
  email_button_color: '#111111',
  email_button_text_color: '#FFFFFF',
  email_footer_text: '',
};
