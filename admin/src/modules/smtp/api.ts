'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface SmtpConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
}

export const smtpApi = {
  get: () => adminFetch<SmtpConfig>('/api/admin/smtp'),
  put: (body: Partial<SmtpConfig>) => adminFetch<SmtpConfig>('/api/admin/smtp', { method: 'PUT', body }),
  test: (to: string) => adminFetch<void>('/api/admin/smtp/test', { method: 'POST', body: { to } }),
};
