'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface UpSellerState {
  has_client_id: boolean;
  has_api_token: boolean;
  connected: boolean;
  stock_sync_enabled: boolean;
  last_sync_at: string | null;
  last_sync_summary: string | null;
}

export interface UpSellerTestResult {
  ok: boolean;
  message: string;
}

export interface UpSellerSyncResult {
  skus_found: number;
  variants_updated: number;
}

export const upsellerApi = {
  getState: () => adminFetch<UpSellerState>('/api/admin/upseller'),
  saveCredentials: (body: { client_id?: string; api_token?: string }) =>
    adminFetch<UpSellerState>('/api/admin/upseller/credentials', { method: 'PUT', body }),
  saveToggles: (body: { stock_sync_enabled?: boolean }) =>
    adminFetch<UpSellerState>('/api/admin/upseller/toggles', { method: 'PUT', body }),
  testConnection: () => adminFetch<UpSellerTestResult>('/api/admin/upseller/test', { method: 'POST' }),
  syncNow: () => adminFetch<UpSellerSyncResult>('/api/admin/upseller/sync', { method: 'POST' }),
};
