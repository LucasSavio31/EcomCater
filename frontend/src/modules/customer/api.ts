'use client';

import { apiFetch, type ApiResult } from '@/lib/api-client';
import {
  clearCustomerSession,
  getCustomerSession,
  setCustomerSession,
} from '@/lib/customer-auth-storage';
import type { Address, AddressInput, Customer, TokenOut } from './types';
import type { Order } from '@/modules/checkout/types';

const BASE = '/api/customers';

let refreshing: Promise<boolean> | null = null;

async function runRefresh(): Promise<boolean> {
  const session = getCustomerSession();
  if (!session?.refreshToken) return false;
  const res = await apiFetch<TokenOut>(`${BASE}/auth/refresh`, {
    method: 'POST',
    body: { refresh_token: session.refreshToken },
  });
  if (res.ok) {
    setCustomerSession(res.data);
    return true;
  }
  clearCustomerSession();
  return false;
}

/** Fetch autenticado do cliente: injeta o Bearer e tenta 1 refresh no 401. */
async function authFetch<T>(
  path: string,
  init: Parameters<typeof apiFetch>[1] = {},
  retry = true,
): Promise<ApiResult<T>> {
  const token = getCustomerSession()?.accessToken ?? null;
  const res = await apiFetch<T>(path, { ...init, token, cache: 'no-store' });
  if (res.ok || res.error.status !== 401 || !retry) return res;

  refreshing = refreshing ?? runRefresh();
  const ok = await refreshing;
  refreshing = null;
  if (!ok) return res;
  return authFetch<T>(path, init, false);
}

export const customerApi = {
  register: (body: {
    full_name: string;
    email: string;
    password: string;
    phone?: string;
    cpf?: string;
  }) => apiFetch<TokenOut>(`${BASE}/auth/register`, { method: 'POST', body }),

  login: (body: { email: string; password: string }) =>
    apiFetch<TokenOut>(`${BASE}/auth/login`, { method: 'POST', body }),

  async logout(): Promise<void> {
    const session = getCustomerSession();
    if (session?.refreshToken) {
      await apiFetch(`${BASE}/auth/logout`, {
        method: 'POST',
        body: { refresh_token: session.refreshToken },
      });
    }
    clearCustomerSession();
  },

  me: () => authFetch<Customer>(`${BASE}/me`),

  updateMe: (body: Partial<{ full_name: string; phone: string; cpf: string; current_password: string; new_password: string }>) =>
    authFetch<Customer>(`${BASE}/me`, { method: 'PATCH', body }),

  listAddresses: () => authFetch<Address[]>(`${BASE}/me/addresses`),
  createAddress: (body: AddressInput) =>
    authFetch<Address>(`${BASE}/me/addresses`, { method: 'POST', body }),
  updateAddress: (id: string, body: AddressInput) =>
    authFetch<Address>(`${BASE}/me/addresses/${id}`, { method: 'PATCH', body }),
  deleteAddress: (id: string) =>
    authFetch<void>(`${BASE}/me/addresses/${id}`, { method: 'DELETE' }),

  myOrders: () => authFetch<Order[]>(`/api/orders`),
  orderPulse: (number: string) =>
    authFetch<{
      number: string;
      status: string;
      payment_status: string;
      fulfillment_status: string;
      event_count: number;
      last_change_at: string | null;
    }>(`/api/orders/${number}/pulse`),
};
