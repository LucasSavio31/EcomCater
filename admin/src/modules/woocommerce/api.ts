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

export const woocommerceApi = {
  listKeys: () => adminFetch<WooKey[]>('/api/admin/woocommerce/keys'),
  createKey: (body: { description?: string; permission: WooPermission }) =>
    adminFetch<WooKeyCreated>('/api/admin/woocommerce/keys', { method: 'POST', body }),
  revokeKey: (id: string) =>
    adminFetch<{ ok: boolean }>(`/api/admin/woocommerce/keys/${id}`, { method: 'DELETE' }),
  listWebhooks: () => adminFetch<WooWebhook[]>('/api/admin/woocommerce/webhooks'),
};
