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

/** SMTP de um domínio (multi-domínio): vendas do domínio X mandam e-mail pelo SMTP de X. */
export interface SmtpDomain {
  hostname: string;
  is_primary: boolean;
  /** status do domínio em Infraestrutura → Domínios */
  status: string;
  smtp: Partial<SmtpConfig> & { configured: boolean; password_set: boolean };
  /** domínio sem SMTP próprio: os e-mails dele saem pelo SMTP principal */
  uses_primary: boolean;
}

export const smtpApi = {
  get: () => adminFetch<SmtpConfig>('/api/admin/smtp'),
  put: (body: Partial<SmtpConfig>) => adminFetch<SmtpConfig>('/api/admin/smtp', { method: 'PUT', body }),
  test: (to: string, site?: string) =>
    adminFetch<{ sent: boolean }>('/api/admin/smtp/test', { method: 'POST', body: { to, site } }),
  domains: () => adminFetch<SmtpDomain[]>('/api/admin/smtp/domains'),
  putDomain: (hostname: string, body: Partial<SmtpConfig>) =>
    adminFetch<SmtpConfig>(`/api/admin/smtp/domains/${encodeURIComponent(hostname)}`, { method: 'PUT', body }),
  removeDomain: (hostname: string) =>
    adminFetch<{ ok: boolean }>(`/api/admin/smtp/domains/${encodeURIComponent(hostname)}`, { method: 'DELETE' }),
};
