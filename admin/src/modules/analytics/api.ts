'use client';

import { adminFetch } from '@/lib/admin-api-client';

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

  meta_capi_enabled: boolean;
  meta_test_event_code: string | null;
  /** só indica se há token salvo — o token nunca volta do servidor */
  meta_capi_token_set: boolean;
  /** só indica se há api_secret salvo — o segredo nunca volta do servidor */
  ga4_api_secret_set: boolean;
}

export interface AnalyticsUpdate
  extends Partial<Omit<AnalyticsConfig, 'meta_capi_token_set' | 'ga4_api_secret_set'>> {
  /** "" limpa o token; ausente mantém o atual */
  meta_capi_access_token?: string;
  /** "" limpa o api_secret; ausente mantém o atual */
  ga4_api_secret?: string;
}

export const analyticsApi = {
  get: () => adminFetch<AnalyticsConfig>('/api/admin/analytics'),
  put: (body: AnalyticsUpdate) =>
    adminFetch<AnalyticsConfig>('/api/admin/analytics', { method: 'PUT', body }),
};
