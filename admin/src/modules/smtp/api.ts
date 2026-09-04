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
  /** cópia oculta (Bcc) que recebe todos os e-mails de PEDIDO do cliente. */
  order_bcc: string | null;
  /** true quando já há uma senha salva no servidor (a senha em si nunca vem). */
  password_set?: boolean;
}

export const smtpApi = {
  get: () => adminFetch<SmtpConfig>('/api/admin/smtp'),
  put: (body: Partial<SmtpConfig>) => adminFetch<SmtpConfig>('/api/admin/smtp', { method: 'PUT', body }),
  test: (to: string) => adminFetch<{ sent: boolean }>('/api/admin/smtp/test', { method: 'POST', body: { to } }),
};
