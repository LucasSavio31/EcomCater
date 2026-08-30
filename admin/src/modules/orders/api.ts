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
        page: query.page ?? 1,
        page_size: query.page_size ?? 50,
      },
    }),
  get: (number: string) => adminFetch<OrderDetail>(`/api/admin/orders/${number}`),
  bulk: (numbers: string[]) =>
    adminFetch<OrderDetail[]>('/api/admin/orders/bulk', { method: 'POST', body: { numbers } }),
  edit: (number: string, body: OrderEditPayload) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}`, { method: 'PATCH', body }),
  remove: (number: string) =>
    adminFetch<void>(`/api/admin/orders/${number}`, { method: 'DELETE' }),
  setStatus: (number: string, status: OrderStatus, message?: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/status`, {
      method: 'POST',
      body: { status, message: message || undefined },
    }),
  addNote: (number: string, message: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/notes`, { method: 'POST', body: { message } }),
  /** Envia pedidos para o carrinho do Melhor Envio (etiqueta gerada lá). */
  sendToMelhorEnvio: (numbers: string[]) =>
    adminFetch<{ results: { number: string; ok: boolean; message: string }[] }>(
      '/api/admin/shipping/melhor-envio/send',
      { method: 'POST', body: { order_numbers: numbers } },
    ),
};
