/**
 * Cliente HTTP do admin — fluxo access/refresh com auto-refresh em 401.
 *
 * - Base: `NEXT_PUBLIC_ADMIN_API_URL` (fallback `NEXT_PUBLIC_API_URL`).
 * - Anexa `Authorization: Bearer <access>` quando há sessão.
 * - Em 401 (ou access token vencido) faz 1 tentativa de refresh via
 *   `POST /api/admin/auth/refresh`, em single-flight, e repete a chamada.
 * - Refresh falhou → limpa a sessão e sinaliza `sessionExpired` (o AuthGuard
 *   redireciona para o login).
 */
'use client';

import {
  clearSession,
  getSession,
  isAccessTokenStale,
  setSession,
  type AdminSession,
} from './auth-storage';

export const ADMIN_API_BASE_URL: string =
  process.env.NEXT_PUBLIC_ADMIN_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  status: number;
}

export type ApiResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: ApiError };

export interface AdminRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Não anexa o Bearer nem tenta refresh (usado no próprio login/refresh). */
  anonymous?: boolean;
}

export class SessionExpiredError extends Error {
  constructor() {
    super('Sessão expirada');
    this.name = 'SessionExpiredError';
  }
}

function buildUrl(path: string, query?: AdminRequestOptions['query']): string {
  const url = new URL(path.startsWith('http') ? path : `${ADMIN_API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

interface RawErrorEnvelope {
  error?: { code?: string; message?: string; details?: Record<string, unknown> };
  detail?: unknown;
}

let refreshInFlight: Promise<AdminSession | null> | null = null;

async function refreshSession(): Promise<AdminSession | null> {
  const current = getSession();
  if (!current) return null;
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(buildUrl('/api/admin/auth/refresh'), {
        method: 'POST',
        headers: { 'content-type': 'application/json', accept: 'application/json' },
        body: JSON.stringify({ refresh_token: current.refreshToken }),
      });
      if (!res.ok) {
        clearSession();
        return null;
      }
      const data = (await res.json()) as {
        access_token: string;
        refresh_token: string;
        expires_in: number;
      };
      return setSession(data);
    } catch {
      clearSession();
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function doFetch(
  path: string,
  options: AdminRequestOptions,
  accessToken: string | null,
): Promise<Response> {
  const { body, query, headers, anonymous: _anon, ...rest } = options;
  const finalHeaders = new Headers(headers);
  finalHeaders.set('accept', 'application/json');

  let finalBody: BodyInit | undefined;
  if (body !== undefined) {
    if (typeof body === 'string' || body instanceof FormData) {
      finalBody = body;
    } else {
      finalHeaders.set('content-type', 'application/json');
      finalBody = JSON.stringify(body);
    }
  }
  if (accessToken) finalHeaders.set('authorization', `Bearer ${accessToken}`);

  return fetch(buildUrl(path, query), { ...rest, headers: finalHeaders, body: finalBody });
}

export async function adminFetch<T>(
  path: string,
  options: AdminRequestOptions = {},
): Promise<ApiResult<T>> {
  const anonymous = options.anonymous ?? false;
  let session = anonymous ? null : getSession();

  if (session && !anonymous && isAccessTokenStale(session)) {
    session = await refreshSession();
    if (!session) return sessionExpired();
  }

  let response: Response;
  try {
    response = await doFetch(path, options, session?.accessToken ?? null);
  } catch (cause) {
    return {
      ok: false,
      error: {
        code: 'network_error',
        message: cause instanceof Error ? cause.message : 'Falha de rede',
        status: 0,
      },
    };
  }

  if (response.status === 401 && !anonymous && getSession()) {
    const refreshed = await refreshSession();
    if (!refreshed) return sessionExpired();
    try {
      response = await doFetch(path, options, refreshed.accessToken);
    } catch (cause) {
      return {
        ok: false,
        error: {
          code: 'network_error',
          message: cause instanceof Error ? cause.message : 'Falha de rede',
          status: 0,
        },
      };
    }
  }

  if (response.status === 204) return { ok: true, data: undefined as T, status: 204 };

  const text = await response.text();
  const parsed: unknown = text ? safeJson(text) : null;

  if (!response.ok) {
    const envelope = (parsed ?? {}) as RawErrorEnvelope;
    return {
      ok: false,
      error: {
        code: envelope.error?.code ?? 'http_error',
        message:
          envelope.error?.message ??
          (typeof envelope.detail === 'string' ? envelope.detail : response.statusText) ??
          'Erro na requisição',
        details: envelope.error?.details,
        status: response.status,
      },
    };
  }

  return { ok: true, data: parsed as T, status: response.status };
}

function sessionExpired(): { ok: false; error: ApiError } {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('ecom:session-expired'));
  }
  return {
    ok: false,
    error: { code: 'session_expired', message: 'Sessão expirada. Faça login novamente.', status: 401 },
  };
}
