'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface Lead {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  source: string;
  coupon_code: string | null;
  subscribed: boolean;
  created_at: string | null;
}

export interface LeadStats {
  total: number;
  subscribed: number;
  from_checkout: number;
  from_popup: number;
  from_coupon: number;
}

export const leadsApi = {
  list: () => adminFetch<Lead[]>('/api/admin/newsletter'),
  stats: () => adminFetch<LeadStats>('/api/admin/newsletter/stats'),
  remove: (ids: string[]) =>
    adminFetch<{ ok: boolean; deleted: number }>('/api/admin/newsletter/delete', {
      method: 'POST',
      body: { ids },
    }),
  campaign: (payload: {
    ids: string[];
    subject: string;
    body: string;
    coupon_code: string | null;
    to_all?: boolean;
  }) =>
    adminFetch<{ sent: number; failed: number }>('/api/admin/newsletter/campaign', {
      method: 'POST',
      body: payload,
    }),
};

export const SOURCE_LABEL: Record<string, string> = {
  home_form: 'Formulário da home',
  popup: 'Popup de captura',
  lead_popup: 'Popup de captura',
  checkout: 'Compra (checkout)',
};
