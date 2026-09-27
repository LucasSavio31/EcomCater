'use client';

import { adminFetch } from '@/lib/admin-api-client';

export type WooPermission = 'read' | 'write' | 'read_write';

export interface WooKey {
  id: string;
  consumer_key: string;
  description: string | null;
  permission: WooPermission;
  last_used_at: string | null;
  created_at: string;
  /** domínio da chave (null = principal) */
  hostname: string | null;
}

/** Domínio na tela de Integrações (acordeão por domínio). */
export interface IntegrationSite {
  hostname: string;
  is_primary: boolean;
  status: string;
}

export interface WooKeyCreated extends WooKey {
  consumer_secret: string;
}

export interface WooWebhook {
  id: number;
  name: string | null;
  status: string;
  topic: string;
  delivery_url: string;
  date_created: string | null;
  date_modified: string | null;
}

/** `hostname` null/omitido = domínio principal. */
export const woocommerceApi = {
  sites: () => adminFetch<IntegrationSite[]>('/api/admin/woocommerce/sites'),
  listKeys: (hostname?: string | null) =>
    adminFetch<WooKey[]>('/api/admin/woocommerce/keys', { query: hostname ? { hostname } : undefined }),
  createKey: (body: { description?: string; permission: WooPermission; hostname?: string | null }) =>
    adminFetch<WooKeyCreated>('/api/admin/woocommerce/keys', { method: 'POST', body }),
  revokeKey: (id: string) =>
    adminFetch<{ ok: boolean }>(`/api/admin/woocommerce/keys/${id}`, { method: 'DELETE' }),
  listWebhooks: (hostname?: string | null) =>
    adminFetch<WooWebhook[]>('/api/admin/woocommerce/webhooks', {
      query: hostname ? { hostname } : undefined,
    }),
};
