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

export interface PaymentMethodBreakdown {
  method: 'credit_card' | 'pix' | 'boleto';
  placed_count: number;
  paid_count: number;
  conversion_pct: number;
  gross_cents: number;
  share_pct: number;
}

export interface RevenueSummary {
  orders_total: number;
  gross_cents: number;
  cost_cents: number;
  shipping_cents: number;
  net_cents: number;
  margin_pct: number;
  refunded_cents: number;
  refunds_count: number;
  canceled_cents: number;
  canceled_count: number;
  series: RevenueSeriesPoint[];
  payment_methods: PaymentMethodBreakdown[];
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
  reportPdfPath: (opts?: { from?: string; to?: string }) => {
    const params = new URLSearchParams();
    if (opts?.from) params.set('date_from', opts.from);
    if (opts?.to) params.set('date_to', opts.to);
    const qs = params.toString();
    return `/api/admin/financial/report.pdf${qs ? `?${qs}` : ''}`;
  },
};
