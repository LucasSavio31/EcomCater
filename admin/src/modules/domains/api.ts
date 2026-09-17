'use client';

import { adminFetch, type ApiResult } from '@/lib/admin-api-client';

export type DomainStatus =
  | 'pending'
  | 'awaiting_nameservers'
  | 'dns_pending'
  | 'provisioning'
  | 'active'
  | 'failed';

export interface DomainRecord {
  id: string;
  hostname: string;
  is_primary: boolean;
  status: DomainStatus;
  dns_managed_by_cloudflare: boolean;
  ssl_status: string;
  last_error: string | null;
  last_checked_at: string | null;
  admin_hostname: string;
  api_hostname: string;
  cloudflare_nameservers: string[] | null;
  dns_confirmed: boolean;
  cache_pages: string[];
  cache_applied_at: string | null;
  switch_requested_at: string | null;
}

export interface CachePageOption {
  key: string;
  label: string;
  description: string;
  ttl_seconds: number;
}

export interface DomainsState {
  has_aapanel: boolean;
  has_cloudflare: boolean;
  aapanel_url: string;
  server_ip: string;
  domains: DomainRecord[];
  cache_page_options: CachePageOption[];
}

export interface DomainsCredentialsIn {
  aapanel_url?: string;
  aapanel_api_key?: string;
  cloudflare_api_token?: string;
  server_ip?: string;
}

export interface CredentialsTestResult {
  aapanel_ok: boolean;
  aapanel_message: string;
  cloudflare_ok: boolean;
  cloudflare_message: string;
}

export const domainsApi = {
  getState: (): Promise<ApiResult<DomainsState>> => adminFetch<DomainsState>('/api/admin/domains'),

  saveCredentials: (body: DomainsCredentialsIn): Promise<ApiResult<DomainsState>> =>
    adminFetch<DomainsState>('/api/admin/domains/credentials', { method: 'PUT', body }),

  testCredentials: (body: DomainsCredentialsIn): Promise<ApiResult<CredentialsTestResult>> =>
    adminFetch<CredentialsTestResult>('/api/admin/domains/credentials/test', {
      method: 'POST',
      body,
    }),

  addOrUpdateDomain: (hostname: string): Promise<ApiResult<DomainRecord>> =>
    adminFetch<DomainRecord>('/api/admin/domains', { method: 'POST', body: { hostname } }),

  retry: (id: string): Promise<ApiResult<DomainRecord>> =>
    adminFetch<DomainRecord>(`/api/admin/domains/${id}/retry`, { method: 'POST' }),

  setPrimary: (id: string): Promise<ApiResult<DomainRecord>> =>
    adminFetch<DomainRecord>(`/api/admin/domains/${id}/set-primary`, { method: 'POST' }),

  remove: (id: string): Promise<ApiResult<void>> =>
    adminFetch<void>(`/api/admin/domains/${id}`, { method: 'DELETE' }),

  saveCachePages: (id: string, pages: string[]): Promise<ApiResult<DomainRecord>> =>
    adminFetch<DomainRecord>(`/api/admin/domains/${id}/cache`, { method: 'PUT', body: { pages } }),
};
