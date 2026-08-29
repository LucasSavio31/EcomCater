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
  free_shipping_threshold_cents?: number | null;
  whatsapp_number?: string | null;
  top_bar_message?: string | null;
  top_bar_enabled: boolean;
  /** Banner principal (hero) da home. */
  hero_enabled: boolean;
  hero_mode: 'carousel' | 'static';
  hero_autoplay_seconds: number;
  /** Selos do rodapé. */
  footer_seals_enabled: boolean;
  footer_seals_json: FooterSeals;
  updated_at?: string | null;
}

export interface FooterSealColumn {
  title: string;
  text: string;
  badges: string[];
}

export interface FooterSeals {
  payment: FooterSealColumn;
  shipping: FooterSealColumn;
  security: FooterSealColumn;
}

const DEFAULT_SEALS: FooterSeals = {
  payment: {
    title: 'Formas de Pagamento',
    text: '',
    badges: ['Pix', 'Boleto', 'Visa', 'Mastercard', 'Amex', 'Elo', 'Hipercard'],
  },
  shipping: { title: 'Formas de Entrega', text: '', badges: ['Correios'] },
  security: {
    title: 'Loja Segura',
    text: 'Site 100% seguro, com criptografia e certificado SSL.',
    badges: ['SSL'],
  },
};

/** Paleta neutra — usada quando a API está fora do ar (build, incidente). */
export const NEUTRAL_THEME: ThemeSettings = {
  primary_color: '#111111',
  secondary_color: '#4B5563',
  accent_color: '#DC2626',
  text_color: '#111827',
  bg_color: '#FFFFFF',
  button_bg_color: '#111111',
  button_text_color: '#FFFFFF',
  button_hover_color: '#DC2626',
  header_bg_color: '#FFFFFF',
  header_text_color: '#111827',
  header_max_width_px: 1280,
  footer_bg_color: '#111827',
  footer_text_color: '#E5E7EB',
  font_family: 'Inter, system-ui, sans-serif',
  logo_url: null,
  top_bar_enabled: false,
  top_bar_message: null,
  hero_enabled: true,
  hero_mode: 'carousel',
  hero_autoplay_seconds: 5,
  footer_seals_enabled: true,
  footer_seals_json: DEFAULT_SEALS,
};
