'use client';

import { adminFetch, ADMIN_API_BASE_URL, type ApiResult } from '@/lib/admin-api-client';
import { getSession } from '@/lib/auth-storage';

/* --------------------------------- Tema --------------------------------- */

export interface Theme {
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  text_color: string;
  bg_color: string;
  /** Botões (estilo Customizer do WordPress / WooCommerce) */
  button_bg_color: string;
  button_text_color: string;
  button_hover_color: string;
  /** Caixas de variação (PDP) + botão "calcular frete" */
  variation_bg_color: string;
  variation_text_color: string;
  variation_border_color: string;
  /** Menu superior (header) */
  header_bg_color: string;
  header_text_color: string;
  header_max_width_px: number;
  /** Menu inferior (rodapé) */
  footer_bg_color: string;
  footer_text_color: string;
  font_family: string;
  free_shipping_threshold_cents: number | null;
  whatsapp_number: string | null;
  top_bar_message: string | null;
  top_bar_enabled: boolean;
  /** Banner principal (hero) */
  hero_enabled: boolean;
  hero_mode: 'carousel' | 'static';
  hero_autoplay_seconds: number;
  /** Selos do rodapé */
  footer_seals_enabled: boolean;
  footer_seals_json: FooterSeals;
  /** Após adicionar ao carrinho: ir para /carrinho (true) ou ficar na PDP (false) */
  cart_redirect_after_add: boolean;
  /** Mini-carrinho lateral ao adicionar */
  mini_cart_enabled: boolean;
  /** Filtros da vitrine (menu "Filtros") */
  filter_size_enabled: boolean;
  filter_color_enabled: boolean;
  filter_material_enabled: boolean;
  filter_price_enabled: boolean;
  filter_category_enabled: boolean;
  /** Modelo do checkout (menu "Checkout") */
  checkout_email_first: boolean;
  checkout_container_width_px: number;
  checkout_items_layout: 'with_thumb' | 'simple';
  checkout_show_coupon: boolean;
  checkout_allow_qty_change: boolean;
  checkout_footer_note: string | null;
  checkout_animated_card: boolean;
  checkout_show_review: boolean;
  checkout_review_position: 'side' | 'top';
  checkout_orderbump_enabled: boolean;
  checkout_orderbump_product_id: string | null;
  checkout_orderbump_product_ids: string[];
  checkout_bg_color: string;
  checkout_header_bg_color: string;
  checkout_header_text_color: string;
  checkout_button_color: string;
  checkout_button_text_color: string;
  checkout_accent_color: string;
  checkout_footer_bg_color: string;
  checkout_footer_text_color: string;
  /** Newsletter (menu "Newsletter") */
  newsletter_enabled: boolean;
  newsletter_title: string;
  newsletter_subtitle: string;
  newsletter_bg_color: string;
  newsletter_text_color: string;
  newsletter_button_color: string;
  newsletter_button_text_color: string;
  discount_badge_enabled: boolean;
  lead_popup_enabled: boolean;
  lead_capture_enabled: boolean;
  lead_popup_title: string;
  lead_popup_subtitle: string;
  lead_popup_coupon_code: string | null;
  lead_popup_bg_color: string;
  lead_popup_text_color: string;
  lead_popup_button_color: string;
  lead_popup_button_text_color: string;
  /** Raio das bordas dos botões (px) */
  button_radius_px: number;
  pdp_qty_selector_enabled: boolean;
  wishlist_enabled: boolean;
  card_hover_zoom_enabled: boolean;
  card_buy_button_enabled: boolean;
  card_buy_button_label: string;
  /** Aviso de cookies de terceiros */
  cookie_consent_enabled: boolean;
  cookie_consent_text: string;
  /** Identidade visual dos e-mails transacionais */
  email_header_bg_color: string;
  email_header_text_color: string;
  email_body_bg_color: string;
  email_text_color: string;
  email_button_color: string;
  email_button_text_color: string;
  email_footer_text: string;
  logo_url?: string | null;
  logo_mobile_url?: string | null;
  favicon_url?: string | null;
}

export interface FooterSealColumn {
  title: string;
  text: string;
  badges: string[];
  images: string[];
  image_urls: string[];
}

export type SealColumn = 'payment' | 'shipping' | 'security';
export interface FooterSeals {
  payment: FooterSealColumn;
  shipping: FooterSealColumn;
  security: FooterSealColumn;
}

export type ThemeImageKind = 'logo' | 'logo_mobile' | 'favicon';

/* ------------------------------- Settings ------------------------------- */

export interface StoreSettings {
  store_name: string;
  legal_name: string | null;
  cnpj: string | null;
  address_json: Record<string, string> | null;
  social_json: Record<string, string> | null;
  contact_phone: string | null;
  contact_whatsapp: string | null;
  payment_flags_json: string[] | null;
  free_shipping_threshold_cents: number | null;
}

/* -------------------------------- Pages -------------------------------- */

export interface ContentPage {
  id: string;
  title: string;
  slug: string;
  body: string;
  is_published: boolean;
  seo_title: string | null;
  seo_description: string | null;
}

export interface ContentPageInput {
  title: string;
  slug?: string;
  body: string;
  is_published: boolean;
  seo_title?: string | null;
  seo_description?: string | null;
}

/* ------------------------------- Banners ------------------------------- */

export interface Banner {
  id: string;
  slot: string;
  title: string | null;
  link_url: string | null;
  alt: string | null;
  position: number;
  starts_at: string | null;
  ends_at: string | null;
  is_active: boolean;
  /** Uma única imagem — redimensionada automaticamente para cada tela. */
  image_url: string | null;
  image_desktop_url: string | null;
}

export interface BannerInput {
  slot: string;
  title?: string | null;
  link_url?: string | null;
  alt?: string | null;
  position: number;
  starts_at?: string | null;
  ends_at?: string | null;
  is_active: boolean;
}

async function uploadMultipart<T>(path: string, form: FormData): Promise<ApiResult<T>> {
  const session = getSession();
  try {
    const res = await fetch(`${ADMIN_API_BASE_URL}${path}`, {
      method: 'POST',
      headers: session ? { authorization: `Bearer ${session.accessToken}` } : undefined,
      body: form,
    });
    const text = await res.text();
    const parsed: unknown = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const env = (parsed ?? {}) as { error?: { message?: string }; detail?: string };
      return {
        ok: false,
        error: {
          code: 'upload_error',
          message: env.error?.message ?? env.detail ?? 'Falha no upload',
          status: res.status,
        },
      };
    }
    return { ok: true, data: parsed as T, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: { code: 'network_error', message: err instanceof Error ? err.message : 'Falha de rede', status: 0 },
    };
  }
}

export const appearanceApi = {
  getTheme: () => adminFetch<Theme>('/api/admin/theme'),
  putTheme: (body: Partial<Theme>) => adminFetch<Theme>('/api/admin/theme', { method: 'PUT', body }),
  uploadThemeImage: (kind: ThemeImageKind, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return uploadMultipart<Theme>(`/api/admin/theme/image/${kind}`, form);
  },
  uploadSealImage: (column: SealColumn, index: number, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return uploadMultipart<Theme>(`/api/admin/theme/seal-image/${column}/${index}`, form);
  },
  removeSealImage: (column: SealColumn, index: number) =>
    adminFetch<Theme>(`/api/admin/theme/seal-image/${column}/${index}`, { method: 'DELETE' }),

  getSettings: () => adminFetch<StoreSettings>('/api/admin/settings'),
  putSettings: (body: Partial<StoreSettings>) =>
    adminFetch<StoreSettings>('/api/admin/settings', { method: 'PUT', body }),

  listPages: () => adminFetch<ContentPage[]>('/api/admin/theme/pages'),
  createPage: (body: ContentPageInput) =>
    adminFetch<ContentPage>('/api/admin/theme/pages', { method: 'POST', body }),
  updatePage: (id: string, body: Partial<ContentPageInput>) =>
    adminFetch<ContentPage>(`/api/admin/theme/pages/${id}`, { method: 'PATCH', body }),
  deletePage: (id: string) => adminFetch<void>(`/api/admin/theme/pages/${id}`, { method: 'DELETE' }),

  listBanners: () => adminFetch<Banner[]>('/api/admin/banners'),
  createBanner: (body: BannerInput) => adminFetch<Banner>('/api/admin/banners', { method: 'POST', body }),
  updateBanner: (id: string, body: Partial<BannerInput>) =>
    adminFetch<Banner>(`/api/admin/banners/${id}`, { method: 'PATCH', body }),
  deleteBanner: (id: string) => adminFetch<void>(`/api/admin/banners/${id}`, { method: 'DELETE' }),
};

/** Upload da imagem do banner (uma só; o front redimensiona por tela). */
export function uploadBannerImage(id: string, file: File): Promise<ApiResult<Banner>> {
  const form = new FormData();
  form.append('file', file);
  return uploadMultipart<Banner>(`/api/admin/banners/${id}/image`, form);
}
