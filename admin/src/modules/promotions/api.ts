'use client';

import { adminFetch } from '@/lib/admin-api-client';

export type PromotionType = 'percent' | 'fixed' | 'free_shipping';

export interface Promotion {
  id: string;
  code: string;
  description: string | null;
  type: PromotionType;
  value: number;
  min_order_cents: number | null;
  max_discount_cents: number | null;
  starts_at: string | null;
  ends_at: string | null;
  usage_limit: number | null;
  usage_limit_per_user: number | null;
  used_count: number;
  is_active: boolean;
}

export interface PromotionInput {
  code: string;
  description?: string | null;
  type: PromotionType;
  value: number;
  min_order_cents?: number | null;
  max_discount_cents?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  usage_limit?: number | null;
  usage_limit_per_user?: number | null;
  is_active: boolean;
}

export const promotionsApi = {
  list: () => adminFetch<Promotion[]>('/api/admin/promotions'),
  create: (body: PromotionInput) => adminFetch<Promotion>('/api/admin/promotions', { method: 'POST', body }),
  update: (id: string, body: Partial<PromotionInput>) =>
    adminFetch<Promotion>(`/api/admin/promotions/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => adminFetch<void>(`/api/admin/promotions/${id}`, { method: 'DELETE' }),
};
