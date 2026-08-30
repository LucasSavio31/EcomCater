'use client';

// TODO: substituir por GET /api/admin/customers quando o backend expuser um
// endpoint dedicado de clientes. Hoje a lista é derivada de GET /api/admin/orders.

import { ordersApi } from '@/modules/orders/api';
import type { ApiResult } from '@/lib/admin-api-client';
import type { OrderListItem } from '@/modules/orders/types';

export interface CustomerSummary {
  email: string;
  orders_count: number;
  total_spent_cents: number;
  last_order_at: string;
  last_status: string;
}

/** Varre as páginas de /orders e agrupa por e-mail. */
export async function fetchCustomers(): Promise<ApiResult<CustomerSummary[]>> {
  const pageSize = 100;
  let page = 1;
  const all: OrderListItem[] = [];

  // Limite defensivo de 20 páginas (2000 pedidos) para não varrer indefinidamente.
  for (let i = 0; i < 20; i += 1) {
    const result = await ordersApi.list({ page, page_size: pageSize });
    if (!result.ok) return result;
    all.push(...result.data.items);
    if (all.length >= result.data.total || result.data.items.length === 0) break;
    page += 1;
  }

  const map = new Map<string, CustomerSummary>();
  for (const order of all) {
    const key = order.email.toLowerCase();
    const orderAt = order.placed_at ?? order.created_at;
    const existing = map.get(key);
    if (existing) {
      existing.orders_count += 1;
      existing.total_spent_cents += order.grand_total_cents;
      if (orderAt > existing.last_order_at) {
        existing.last_order_at = orderAt;
        existing.last_status = order.status;
      }
    } else {
      map.set(key, {
        email: order.email,
        orders_count: 1,
        total_spent_cents: order.grand_total_cents,
        last_order_at: orderAt,
        last_status: order.status,
      });
    }
  }

  const list = [...map.values()].sort((a, b) => b.total_spent_cents - a.total_spent_cents);
  return { ok: true, data: list, status: 200 };
}

export const customersApi = {
  ordersByEmail: (email: string) => ordersApi.list({ q: email, page_size: 100 }),
};
