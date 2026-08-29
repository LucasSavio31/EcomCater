'use client';

import { adminFetch } from '@/lib/admin-api-client';
import type { OrderDetail, OrderListItem, OrderStatus } from './types';
import type { Paginated } from '@/modules/catalog/types';

export interface OrderListQuery {
  status?: OrderStatus | '';
  q?: string;
  page?: number;
  page_size?: number;
}

export const ordersApi = {
  list: (query: OrderListQuery) =>
    adminFetch<Paginated<OrderListItem>>('/api/admin/orders', {
      query: {
        status: query.status || undefined,
        q: query.q || undefined,
        page: query.page ?? 1,
        page_size: query.page_size ?? 20,
      },
    }),
  get: (number: string) => adminFetch<OrderDetail>(`/api/admin/orders/${number}`),
  setStatus: (number: string, status: OrderStatus, message?: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/status`, {
      method: 'POST',
      body: { status, message: message || undefined },
    }),
  addNote: (number: string, message: string) =>
    adminFetch<OrderDetail>(`/api/admin/orders/${number}/notes`, { method: 'POST', body: { message } }),
};
