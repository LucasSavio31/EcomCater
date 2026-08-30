'use client';

import { apiFetch, type ApiResult } from '@/lib/api-client';
import { getCustomerToken } from '@/lib/customer-auth-storage';
import type {
  ChargePayload,
  ChargeResult,
  CheckoutPayload,
  Order,
  PaymentMethods,
  PaymentStatus,
} from './types';

function checkoutFetch<T>(
  path: string,
  init: Parameters<typeof apiFetch>[1] = {},
): Promise<ApiResult<T>> {
  return apiFetch<T>(path, {
    ...init,
    credentials: 'include',
    token: getCustomerToken(),
    cache: 'no-store',
  });
}

export const checkoutApi = {
  paymentMethods: () => checkoutFetch<PaymentMethods>('/api/payment/methods'),

  placeOrder: (body: CheckoutPayload) =>
    checkoutFetch<
      Order & {
        auth?: { access_token: string; refresh_token: string; expires_in: number } | null;
      }
    >('/api/orders/checkout', { method: 'POST', body }),

  charge: (body: ChargePayload) =>
    checkoutFetch<ChargeResult>('/api/payment/charge', { method: 'POST', body }),

  paymentStatus: (orderNumber: string) =>
    checkoutFetch<PaymentStatus>(`/api/payment/status/${orderNumber}`),

  getOrder: (orderNumber: string, email?: string) =>
    checkoutFetch<Order>(`/api/orders/${orderNumber}`, {
      query: email ? { email } : undefined,
    }),
};
