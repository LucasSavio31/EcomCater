'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface DashboardRecentOrder {
  number: string;
  status: string;
  payment_status: string;
  total_cents: number;
  email: string;
  placed_at: string;
}

export interface DashboardData {
  orders_today: number;
  orders_pending: number;
  revenue_month_cents: number;
  low_stock_count: number;
  recent_orders: DashboardRecentOrder[];
}

export const dashboardApi = {
  get: (range?: { from?: string; to?: string }) =>
    adminFetch<DashboardData>('/api/admin/dashboard', {
      query: {
        date_from: range?.from || undefined,
        date_to: range?.to || undefined,
      },
    }),
};
