'use client';

import { adminFetch, type ApiError, type ApiResult } from '@/lib/admin-api-client';
import { clearSession, setSession } from '@/lib/auth-storage';
import type { AdminUser, TokenPair } from './types';

export type LoginOutcome =
  | { ok: true; mfaRequired: false }
  | { ok: true; mfaRequired: true; mfaToken: string }
  | { ok: false; error: ApiError };

interface LoginResponse extends Partial<TokenPair> {
  mfa_required: boolean;
  mfa_token?: string;
}

export async function login(email: string, password: string): Promise<LoginOutcome> {
  const result = await adminFetch<LoginResponse>('/api/admin/auth/login', {
    method: 'POST',
    body: { email, password },
    anonymous: true,
  });
  if (!result.ok) return { ok: false, error: result.error };
  if (result.data.mfa_required) {
    return { ok: true, mfaRequired: true, mfaToken: result.data.mfa_token ?? '' };
  }
  setSession(result.data as TokenPair);
  return { ok: true, mfaRequired: false };
}

/** Segundo passo do login quando a conta tem 2FA ativo. */
export async function verifyMfa(mfaToken: string, code: string): Promise<ApiResult<TokenPair>> {
  const result = await adminFetch<TokenPair>('/api/admin/auth/2fa/verify', {
    method: 'POST',
    body: { mfa_token: mfaToken, code },
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

export function forgotPassword(email: string): Promise<ApiResult<{ ok: boolean }>> {
  return adminFetch<{ ok: boolean }>('/api/admin/auth/forgot-password', {
    method: 'POST',
    body: { email },
  });
}

export function resetPassword(token: string, newPassword: string): Promise<ApiResult<void>> {
  return adminFetch<void>('/api/admin/auth/reset-password', {
    method: 'POST',
    body: { token, new_password: newPassword },
  });
}

export async function logout(): Promise<void> {
  clearSession();
}
