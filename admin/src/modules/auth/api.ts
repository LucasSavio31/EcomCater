'use client';

import { adminFetch, type ApiResult } from '@/lib/admin-api-client';
import { clearSession, setSession } from '@/lib/auth-storage';
import type { AdminUser, TokenPair } from './types';

export async function login(email: string, password: string): Promise<ApiResult<TokenPair>> {
  const result = await adminFetch<TokenPair>('/api/admin/auth/login', {
    method: 'POST',
    body: { email, password },
    anonymous: true,
  });
  if (result.ok) setSession(result.data);
  return result;
}

export function fetchMe(): Promise<ApiResult<AdminUser>> {
  return adminFetch<AdminUser>('/api/admin/auth/me', { method: 'GET' });
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<ApiResult<void>> {
  return adminFetch<void>('/api/admin/auth/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

export async function logout(): Promise<void> {
  clearSession();
}
