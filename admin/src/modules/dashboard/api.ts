'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface SeriesPoint {
  label: string;
  cents: number;
}
export interface AbcPoint {
  name: string;
  revenue_cents: number;
  cum_pct: number;
  cls: 'A' | 'B' | 'C';
}
export interface TopProduct {
  name: string;
  sku: string;
  units: number;
  revenue_cents: number;
}

export type DashboardMetric = 'revenue' | 'canceled' | 'refunded';

export interface DashboardData {
  window_days: number;
  orders_period: number;
  orders_pending: number;
  orders_late: number;
  orders_to_ship: number;
  orders_canceled: number;
  orders_refunded: number;
  revenue_period_cents: number;
  total_orders_all_time: number;
  series_metric: DashboardMetric;
  series_current: SeriesPoint[];
  series_previous: SeriesPoint[];
  abc_curve: AbcPoint[];
  top_products: TopProduct[];
}

export const dashboardApi = {
  get: (opts?: { from?: string; to?: string; metric?: DashboardMetric }) =>
    adminFetch<DashboardData>('/api/admin/dashboard', {
      query: {
        date_from: opts?.from || undefined,
        date_to: opts?.to || undefined,
        metric: opts?.metric || undefined,
      },
    }),
};
