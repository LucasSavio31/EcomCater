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

export const leadsApi = {
  list: () => adminFetch<Lead[]>('/api/admin/newsletter'),
};

export const SOURCE_LABEL: Record<string, string> = {
  home_form: 'Formulário da home',
  popup: 'Popup de captura',
  lead_popup: 'Popup de captura',
  checkout: 'Compra (checkout)',
};
