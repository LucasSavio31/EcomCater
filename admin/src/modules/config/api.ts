'use client';

import { adminFetch } from '@/lib/admin-api-client';

/* ------------------------------- Módulos ------------------------------- */

export interface ModuleInfo {
  slug: string;
  label: string;
  kind: string;
  toggleable: boolean;
  enabled: boolean;
  config: Record<string, unknown>;
}

/* -------------------------------- Frete -------------------------------- */

export interface ShippingConfig {
  active_provider: string;
  origin_zip: string;
  melhor_envio_token: string;
  melhor_envio_sandbox: boolean;
  webhook_token: string;
  /** URL de webhook que o lojista cadastra no painel do provedor (read-only). */
  webhook_url?: string;
  default_package: {
    weight_grams?: number;
    length_mm?: number;
    width_mm?: number;
    height_mm?: number;
  };
  free_shipping_services: string[];
  /** Frete grátis para tudo — checkout não calcula frete */
  free_shipping_all?: boolean;
}

export interface ShippingQuoteRate {
  service: string;
  carrier: string;
  price_cents: number;
  delivery_days: number;
}

/* ------------------------------ Pagamento ----------------------------- */

export interface PaymentConfig {
  active_provider: 'appmax' | 'fake';
  appmax_access_token: string;
  appmax_sandbox: boolean;
  appmax_webhook_secret: string;
  methods: {
    credit_card: boolean;
    pix: boolean;
    boleto: boolean;
  };
  max_installments: number;
  /** URL de webhook que o lojista cadastra no painel do gateway (read-only). */
  webhook_url?: string;
}

export interface PaymentRecord {
  id: string;
  order_number: string;
  provider: string;
  method: string;
  status: string;
  amount_cents: number;
  installments: number | null;
  created_at: string;
}

export interface WebhookEvent {
  id: string;
  provider: string;
  provider_event_id: string;
  signature_valid: boolean;
  processed_at: string | null;
  order_id: string | null;
  created_at: string;
}

export const configApi = {
  listModules: () => adminFetch<ModuleInfo[]>('/api/admin/modules'),
  patchModule: (slug: string, body: { enabled?: boolean; config?: Record<string, unknown> }) =>
    adminFetch<ModuleInfo>(`/api/admin/modules/${slug}`, { method: 'PATCH', body }),

  getShipping: () => adminFetch<ShippingConfig>('/api/admin/shipping/config'),
  putShipping: (body: Partial<ShippingConfig>) =>
    adminFetch<ShippingConfig>('/api/admin/shipping/config', { method: 'PUT', body }),
  testQuote: (destZip: string) =>
    adminFetch<{ rates: ShippingQuoteRate[] }>('/api/admin/shipping/test-quote', {
      method: 'POST',
      query: { dest_zip: destZip },
    }),

  getPayment: () => adminFetch<PaymentConfig>('/api/admin/payment/config'),
  putPayment: (body: Partial<PaymentConfig>) =>
    adminFetch<PaymentConfig>('/api/admin/payment/config', { method: 'PUT', body }),
  listPayments: () => adminFetch<PaymentRecord[]>('/api/admin/payment/payments'),
  refund: (orderNumber: string, amountCents?: number) =>
    adminFetch<void>(`/api/admin/payment/refund/${orderNumber}`, {
      method: 'POST',
      body: { amount_cents: amountCents ?? undefined },
    }),
  listWebhookEvents: () => adminFetch<WebhookEvent[]>('/api/admin/payment/webhook-events'),
  reprocessWebhook: (id: string) =>
    adminFetch<void>(`/api/admin/payment/webhook-events/${id}/reprocess`, { method: 'POST' }),
};
