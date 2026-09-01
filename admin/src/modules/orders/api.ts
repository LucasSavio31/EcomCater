'use client';

import { adminFetch } from '@/lib/admin-api-client';
import type { OrderAddress, OrderDetail, OrderListItem, OrderStatus } from './types';
import type { Paginated } from '@/modules/catalog/types';

export interface OrderListQuery {
  status?: OrderStatus | '';
  payment_status?: 'pending' | 'paid' | 'canceled' | 'refunded' | '';
  q?: string;
  date_from?: string;
  date_to?: string;
  /** Atalhos do painel: 'to_ship' | 'late' | 'today'. */
  bucket?: string;
  page?: number;
  page_size?: number;
}

export interface OrderEditPayload {
  email?: string;
  cpf?: string | null;
  customer_note?: string | null;
  shipping_address?: Partial<OrderAddress>;
  shipping_service?: { tracking_code?: string };
  items?: {
    id: string;
    variant_label?: string | null;
    cor?: string | null;
    numero?: string | null;
    name?: string;
  }[];
}

export const ordersApi = {
  list: (query: OrderListQuery) =>
    adminFetch<Paginated<OrderListItem>>('/api/admin/orders', {
      query: {
        status: query.status || undefined,
        payment_status: query.payment_status || undefined,
        q: query.q || undefined,
        date_from: query.date_from || undefined,
        date_to: query.date_to || undefined,
        bucket: query.bucket || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 50,
      },
    }),
  get: (number: string) => adminFetch<OrderDetail>(`/api/admin/orders/${number}`),
  pulse: (number: string) =>
    adminFetch<{
      number: string;
      status: string;
      payment_status: string;
      fulfillment_status: string;
      event_count: number;
      last_change_at: string | null;
    }>(`/api/admin/orders/${number}/pulse`),
  bulk: (numbers: string[]) =>
    adminFetch<OrderDetail[]>('/api/admin/orders/bulk', { method: 'POST', body: { numbers } }),
  edit: (number: string, body: OrderEditPayload) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}`, { method: 'PATCH', body }),
  remove: (number: string) =>
    adminFetch<void>(`/api/admin/orders/${number}`, { method: 'DELETE', query: { confirm: true } }),
  setStatus: (number: string, status: OrderStatus, message?: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/status`, {
      method: 'POST',
      body: { status, message: message || undefined },
    }),
  /** Muda o status de vários pedidos de uma vez. */
  bulkStatus: (numbers: string[], status: OrderStatus, message?: string) =>
    adminFetch<{ results: { number: string; ok: boolean; message?: string }[] }>(
      '/api/admin/orders/bulk-status',
      { method: 'POST', body: { numbers, status, message: message || undefined } },
    ),
  addNote: (number: string, message: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/notes`, { method: 'POST', body: { message } }),
  /**
   * Gera a etiqueta no Melhor Envio (carrinho → compra c/ saldo → gerar → PDF).
   * `buy=false` só adiciona ao carrinho do ME.
   */
  sendToMelhorEnvio: (numbers: string[], buy = true) =>
    adminFetch<{
      results: {
        number: string;
        ok: boolean;
        message: string;
        shipment_id?: string | null;
        protocol?: string | null;
        tracking_code?: string | null;
        label_url?: string | null;
        me_status?: string | null;
      }[];
    }>('/api/admin/shipping/melhor-envio/send', {
      method: 'POST',
      body: { order_numbers: numbers, buy },
    }),
  /** Força agora a sincronização de rastreio/status com o Melhor Envio. */
  syncMelhorEnvioTracking: () =>
    adminFetch<{ ran: boolean; checked?: number; updated?: number; reason?: string }>(
      '/api/admin/shipping/melhor-envio/sync-tracking',
      { method: 'POST' },
    ),
  /** Estado da rotina automática de sincronização de rastreio. */
  melhorEnvioSyncStatus: () =>
    adminFetch<{
      enabled: boolean;
      running: boolean;
      interval_seconds: number;
      last_run_at: string | null;
      last_run_source: 'auto' | 'manual' | null;
      seconds_since_last_run: number | null;
      next_run_at: string | null;
      seconds_until_next_run: number | null;
      runs: number;
      last_result: { ran?: boolean; checked?: number; updated?: number } | null;
    }>('/api/admin/shipping/melhor-envio/sync-status'),
};
