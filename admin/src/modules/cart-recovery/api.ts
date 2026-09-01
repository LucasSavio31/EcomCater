'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface AbandonedCart {
  id: string;
  email: string;
  total_cents: number;
  items_count: number;
  reminders_sent: number;
  recovered: boolean;
  created_at: string | null;
  last_email_at: string | null;
}

export interface RecoveryMessage {
  id: string;
  position: number;
  delay_minutes: number;
  subject: string;
  body: string;
  is_active: boolean;
}

export type RecoveryMessageInput = Omit<RecoveryMessage, 'id'>;

export interface RecoveryStats {
  total: number;
  recovered: number;
  abandoned: number;
  reminded: number;
  recovered_after_email: number;
  recovery_rate_pct: number;
  email_recovery_rate_pct: number;
  recovered_revenue_cents: number;
}

const BASE = '/api/admin/cart-recovery';

export const cartRecoveryApi = {
  stats: () => adminFetch<RecoveryStats>(`${BASE}/stats`),
  listCarts: () => adminFetch<AbandonedCart[]>(`${BASE}/carts`),
  deleteCarts: (ids: string[]) =>
    adminFetch<{ ok: boolean; deleted: number }>(`${BASE}/carts/delete`, {
      method: 'POST',
      body: { ids },
    }),
  listMessages: () => adminFetch<RecoveryMessage[]>(`${BASE}/messages`),
  createMessage: (body: RecoveryMessageInput) =>
    adminFetch<RecoveryMessage>(`${BASE}/messages`, { method: 'POST', body }),
  updateMessage: (id: string, body: RecoveryMessageInput) =>
    adminFetch<RecoveryMessage>(`${BASE}/messages/${id}`, { method: 'PATCH', body }),
  deleteMessage: (id: string) =>
    adminFetch<void>(`${BASE}/messages/${id}`, { method: 'DELETE' }),
  runNow: () => adminFetch<{ sent: number }>(`${BASE}/run-now`, { method: 'POST' }),
};
