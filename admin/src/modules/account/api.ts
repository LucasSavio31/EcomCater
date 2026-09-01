'use client';

import { adminFetch, type ApiResult } from '@/lib/admin-api-client';
import type { AdminUser } from '@/modules/auth';

export interface TwoFaSetup {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
}

export const accountApi = {
  updateProfile: (body: { name?: string; email?: string }): Promise<ApiResult<AdminUser>> =>
    adminFetch<AdminUser>('/api/admin/auth/me', { method: 'PATCH', body }),

  start2fa: (): Promise<ApiResult<TwoFaSetup>> =>
    adminFetch<TwoFaSetup>('/api/admin/auth/2fa/start', { method: 'POST' }),

  confirm2fa: (code: string): Promise<ApiResult<{ recovery_codes: string[] }>> =>
    adminFetch<{ recovery_codes: string[] }>('/api/admin/auth/2fa/confirm', {
      method: 'POST',
      body: { code },
    }),

  disable2fa: (password: string): Promise<ApiResult<void>> =>
    adminFetch<void>('/api/admin/auth/2fa/disable', { method: 'POST', body: { password } }),
};
