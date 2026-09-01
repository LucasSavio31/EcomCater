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

/**
 * Item no formato canônico do tracker. `buildItem*()` em `items.ts` é a ÚNICA
 * fonte destes objetos — as páginas não montam item na mão.
 */
export interface TrackItem {
  id: string;
  name: string;
  price: number; // em reais (não centavos)
  quantity?: number;
  /** categoria "folha"; `categoryPath` gera item_category..5 */
  category?: string | null;
  categoryPath?: string | null;
  variant?: string | null;
  brand?: string | null;
  /** desconto monetário UNITÁRIO em reais (só quando há desconto real) */
  discount?: number;
  coupon?: string;
  /** contexto de lista, preservado view_item_list → select_item → view_item */
  item_list_id?: string;
  item_list_name?: string;
  /** posição na lista de origem (GA4 `index`) */
  index?: number;
}

/** Promoção interna (banner/campanha) — GA4 view_promotion / select_promotion. */
export interface TrackPromotion {
  promotion_id: string;
  promotion_name?: string;
  creative_name?: string;
  creative_slot?: string;
  items?: TrackItem[];
}

export type TrackEvent =
  | 'page_view'
  | 'view_promotion'
  | 'select_promotion'
  | 'view_item'
  | 'view_item_list'
  | 'select_item'
  | 'search'
  | 'view_search_results'
  | 'add_to_cart'
  | 'remove_from_cart'
  | 'view_cart'
  | 'begin_checkout'
  | 'add_shipping_info'
  | 'add_payment_info'
  | 'purchase'
  | 'refund'
  | 'add_to_wishlist'
  | 'login'
  | 'sign_up'
  | 'share'
  | 'generate_lead';
