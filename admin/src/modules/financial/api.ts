'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface RevenueSeriesPoint {
  label: string;
  gross_cents: number;
  net_cents: number;
  refunded_cents: number;
  canceled_cents: number;
  orders: number;
}

export interface RevenueSummary {
  orders_total: number;
  gross_cents: number;
  cost_cents: number;
  net_cents: number;
  margin_pct: number;
  refunded_cents: number;
  refunds_count: number;
  canceled_cents: number;
  canceled_count: number;
  series: RevenueSeriesPoint[];
  window: { from: string; to: string };
}

export const financialApi = {
  summary: (opts?: { from?: string; to?: string }) =>
    adminFetch<RevenueSummary>('/api/admin/financial/summary', {
      query: {
        date_from: opts?.from || undefined,
        date_to: opts?.to || undefined,
      },
    }),
};
