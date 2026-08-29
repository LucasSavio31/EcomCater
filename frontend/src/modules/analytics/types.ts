/** Config pública de rastreamento (`GET /api/analytics/config`) — sem segredos. */
export interface AnalyticsConfig {
  gtm_enabled: boolean;
  gtm_container_id: string | null;

  ga4_enabled: boolean;
  ga4_measurement_id: string | null;

  google_ads_enabled: boolean;
  google_ads_conversion_id: string | null;
  google_ads_purchase_label: string | null;

  meta_pixel_enabled: boolean;
  meta_pixel_id: string | null;
}

export const DISABLED_ANALYTICS: AnalyticsConfig = {
  gtm_enabled: false,
  gtm_container_id: null,
  ga4_enabled: false,
  ga4_measurement_id: null,
  google_ads_enabled: false,
  google_ads_conversion_id: null,
  google_ads_purchase_label: null,
  meta_pixel_enabled: false,
  meta_pixel_id: null,
};

/** Item no formato canônico do nosso tracker (convertido p/ GA4 e Meta). */
export interface TrackItem {
  id: string;
  name: string;
  price: number; // em reais (não centavos)
  quantity?: number;
  category?: string | null;
  variant?: string | null;
  brand?: string | null;
}

export type TrackEvent =
  | 'view_item'
  | 'view_item_list'
  | 'select_item'
  | 'search'
  | 'add_to_cart'
  | 'remove_from_cart'
  | 'view_cart'
  | 'begin_checkout'
  | 'add_shipping_info'
  | 'add_payment_info'
  | 'purchase'
  | 'add_to_wishlist'
  | 'sign_up'
  | 'generate_lead';
