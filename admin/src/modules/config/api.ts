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
  /** O GET não devolve o token (segurança) — use `has_token`. Enviar vazio no PUT = manter. */
  melhor_envio_token?: string;
  /** true quando já há um token salvo. */
  has_token?: boolean;
  /** true quando o token vem do .env do servidor (não removível pelo painel). */
  token_from_env?: boolean;
  /** ISO 8601 de expiração do access_token (quando conhecido). */
  token_expires_at?: string | null;
  melhor_envio_sandbox: boolean;
  /** CPF do responsável pelo envio — obrigatório p/ gerar etiqueta no ME. */
  sender_cpf?: string;
  /** Impressão de etiquetas: térmica 10x15 (1/página) ou A4 4-up. */
  label_format?: 'termica_10x15' | 'a4_4up';
  /** Anexar a Declaração de Conteúdo após cada etiqueta. */
  print_declaration?: boolean;
  /** Intervalo (segundos) da rotina que consulta a API do Melhor Envio. 0 = padrão do servidor; mínimo 120. */
  me_poll_interval_seconds?: number;
  webhook_token?: string;
  /** OAuth: app Melhor Envio. */
  melhor_envio_client_id?: string;
  melhor_envio_client_secret?: string;
  has_client_secret?: boolean;
  /** Redirect URI a cadastrar no app do Melhor Envio (read-only). */
  oauth_redirect_uri?: string;
  /** URL de webhook que o lojista cadastra no painel do provedor (read-only). */
  webhook_url?: string;
  default_package: {
    weight_grams?: number;
    length_mm?: number;
    width_mm?: number;
    height_mm?: number;
  };
  /** Serviços mostrados ao cliente (minúsculas): ex. ['pac','sedex']. */
  allowed_services?: string[];
  free_shipping_services: string[];
  /** Frete grátis para tudo — checkout não calcula frete */
  free_shipping_all?: boolean;
  /** Frete grátis automático quando o subtotal do pedido atinge este valor (centavos). */
  free_shipping_min_cents?: number | null;
}

export interface ShippingQuoteRate {
  service: string;
  carrier: string;
  price_cents: number;
  delivery_days: number;
}

/* ------------------------------ Pagamento ----------------------------- */

export interface PaymentProviderOut {
  enabled: boolean;
  sandbox?: boolean;
  has_token?: boolean;
  has_webhook_secret?: boolean;
}

export interface PaymentConfig {
  providers: Record<string, PaymentProviderOut>;
  /** método -> slug do provedor que atende (ausente = método desligado) */
  method_providers: Record<string, string>;
  max_installments: number;
  /** URL de webhook por provedor ativo, pra cadastrar no painel do gateway. */
  webhook_urls: Record<string, string>;
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
  melhorEnvioAuthorizeUrl: () =>
    adminFetch<{ url: string }>('/api/admin/shipping/melhor-envio/authorize'),
  melhorEnvioDisconnect: () =>
    adminFetch<{ ok: boolean }>('/api/admin/shipping/melhor-envio/disconnect', { method: 'POST' }),
  testQuote: (destZip: string) =>
    adminFetch<{ rates: ShippingQuoteRate[] }>('/api/admin/shipping/test-quote', {
      method: 'POST',
      query: { dest_zip: destZip },
    }),

  getPayment: () => adminFetch<PaymentConfig>('/api/admin/payment/config'),
  putPaymentProvider: (slug: string, body: { enabled?: boolean; config?: Record<string, unknown> }) =>
    adminFetch<PaymentConfig>(`/api/admin/payment/config/providers/${slug}`, { method: 'PUT', body }),
  putPaymentMethodProviders: (body: {
    credit_card?: string | null;
    pix?: string | null;
    boleto?: string | null;
    max_installments?: number;
  }) => adminFetch<PaymentConfig>('/api/admin/payment/config/method-providers', { method: 'PUT', body }),
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
