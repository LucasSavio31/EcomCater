'use client';

import { adminFetch } from '@/lib/admin-api-client';
import { ordersApi } from '@/modules/orders/api';

export interface CustomerListItem {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  cpf: string | null;
  is_active: boolean;
  created_at: string | null;
  orders_count: number;
  total_spent_cents: number;
}

export interface CustomerAddress {
  id: string;
  label: string;
  recipient_name: string;
  zip: string;
  street: string;
  number: string;
  complement: string | null;
  district: string;
  city: string;
  state: string;
  country: string;
  is_default: boolean;
}

export type CustomerAddressInput = Omit<CustomerAddress, 'id'>;

export interface CustomerOrderRef {
  number: string;
  status: string;
  payment_status: string;
  grand_total_cents: number;
  created_at: string | null;
  active: boolean;
}

export interface CustomerDetail {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  cpf: string | null;
  is_active: boolean;
  created_at: string | null;
  addresses: CustomerAddress[];
  orders: CustomerOrderRef[];
}

export interface CustomerPatch {
  full_name?: string;
  email?: string;
  phone?: string | null;
  cpf?: string | null;
  is_active?: boolean;
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const BASE = '/api/admin/customers';

export const customersApi = {
  list: (q: string, page: number) =>
    adminFetch<Paginated<CustomerListItem>>(BASE, {
      query: { q: q || undefined, page, page_size: 25 },
    }),
  get: (id: string) => adminFetch<CustomerDetail>(`${BASE}/${id}`),
  update: (id: string, body: CustomerPatch) =>
    adminFetch<CustomerDetail & { orders_updated: number }>(`${BASE}/${id}`, {
      method: 'PATCH',
      body,
    }),
  addAddress: (id: string, body: CustomerAddressInput) =>
    adminFetch<CustomerAddress>(`${BASE}/${id}/addresses`, { method: 'POST', body }),
  updateAddress: (id: string, aid: string, body: CustomerAddressInput) =>
    adminFetch<CustomerAddress>(`${BASE}/${id}/addresses/${aid}`, { method: 'PATCH', body }),
  deleteAddress: (id: string, aid: string) =>
    adminFetch<void>(`${BASE}/${id}/addresses/${aid}`, { method: 'DELETE' }),
  ordersByEmail: (email: string) => ordersApi.list({ q: email, page_size: 100 }),
};
