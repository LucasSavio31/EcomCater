/** Resposta de `GET /api/theme` (linha única `theme_settings`, com fallback no back). */
export interface ThemeSettings {
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  text_color: string;
  bg_color: string;
  font_family: string;
  logo_key?: string | null;
  logo_mobile_key?: string | null;
  logo_url?: string | null;
  favicon_key?: string | null;
  free_shipping_threshold_cents?: number | null;
  whatsapp_number?: string | null;
  top_bar_message?: string | null;
  top_bar_enabled: boolean;
  updated_at?: string | null;
}

/** Paleta neutra — usada quando a API está fora do ar (build, incidente). */
export const NEUTRAL_THEME: ThemeSettings = {
  primary_color: '#111111',
  secondary_color: '#4B5563',
  accent_color: '#DC2626',
  text_color: '#111827',
  bg_color: '#FFFFFF',
  font_family: 'Inter, system-ui, sans-serif',
  logo_url: null,
  top_bar_enabled: false,
  top_bar_message: null,
};
