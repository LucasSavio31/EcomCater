'use client';

/**
 * Guarda os tokens do cliente logado (loja) no `localStorage`, com cache em
 * memória. Espelha a estratégia do admin, porém com chave própria — as duas
 * áreas têm sessões independentes.
 */

const KEY = 'ecom:customer:session';

export interface CustomerSession {
  accessToken: string;
  refreshToken: string;
  /** epoch ms em que o access token expira (com folga de 30s). */
  expiresAt: number;
}

let cache: CustomerSession | null = null;
let hydrated = false;

function hydrate(): void {
  if (hydrated || typeof window === 'undefined') return;
  hydrated = true;
  try {
    const raw = window.localStorage.getItem(KEY);
    cache = raw ? (JSON.parse(raw) as CustomerSession) : null;
  } catch {
    cache = null;
  }
}

export function getCustomerSession(): CustomerSession | null {
  hydrate();
  return cache;
}

export function getCustomerToken(): string | null {
  return getCustomerSession()?.accessToken ?? null;
}

export function setCustomerSession(
  data: { access_token: string; refresh_token: string; expires_in: number },
): CustomerSession {
  const session: CustomerSession = {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    expiresAt: Date.now() + Math.max(0, data.expires_in - 30) * 1000,
  };
  cache = session;
  hydrated = true;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    /* modo privado / storage cheio — a sessão vale só nesta aba */
  }
  return session;
}

export function clearCustomerSession(): void {
  cache = null;
  hydrated = true;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
}
