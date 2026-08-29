'use client';

import { apiFetch, type ApiResult } from '@/lib/api-client';
import { getCustomerToken } from '@/lib/customer-auth-storage';
import type { Cart, ShippingOption } from './types';

/**
 * Cliente do carrinho. Toda chamada vai com `credentials: 'include'` para o
 * cookie httpOnly `cart_token` (convidado) ir e voltar, e com o Bearer do
 * cliente logado quando houver — o backend funde os dois.
 */
function cartFetch<T>(path: string, init: Parameters<typeof apiFetch>[1] = {}): Promise<ApiResult<T>> {
  return apiFetch<T>(path, {
    ...init,
    credentials: 'include',
    token: getCustomerToken(),
    cache: 'no-store',
  });
}

export const cartApi = {
  get: () => cartFetch<Cart>('/api/cart'),

  addItem: (variantId: string, quantity = 1) =>
    cartFetch<Cart>('/api/cart/items', {
      method: 'POST',
      body: { variant_id: variantId, quantity },
    }),

  updateItem: (itemId: string, quantity: number) =>
    cartFetch<Cart>(`/api/cart/items/${itemId}`, { method: 'PATCH', body: { quantity } }),

  removeItem: (itemId: string) =>
    cartFetch<Cart>(`/api/cart/items/${itemId}`, { method: 'DELETE' }),

  setZip: (zip: string) =>
    cartFetch<Cart>('/api/cart/zip', { method: 'PUT', body: { zip: zip.replace(/\D/g, '') } }),

  applyCoupon: (code: string) =>
    cartFetch<Cart>('/api/cart/coupon', { method: 'POST', body: { code } }),

  removeCoupon: () => cartFetch<Cart>('/api/cart/coupon', { method: 'DELETE' }),

  shippingOptions: () => cartFetch<ShippingOption[]>('/api/cart/shipping-options'),

  selectShipping: (serviceId: string) =>
    cartFetch<Cart>('/api/cart/shipping', { method: 'POST', body: { service_id: serviceId } }),
};
