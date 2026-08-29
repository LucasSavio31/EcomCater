/**
 * Armazenamento de sessão do admin.
 *
 * Estratégia: `localStorage` + cache em memória.
 *  - O painel é uma app separada (porta 3001 em dev, `/administracao` atrás do
 *    LiteSpeed em prod) e a API é cross-origin, devolvendo os tokens no corpo
 *    JSON do login. Cookies httpOnly exigiriam a API setando cookie + CORS com
 *    credentials + CSRF — nada disso existe hoje. Bearer via header é o que a
 *    API espera.
 *  - Mitigações: só o refresh token persiste "de longo prazo"; access token é
 *    curto (15 min) e revalidado por auto-refresh; `logout` limpa tudo; XSS
 *    continua sendo o vetor a vigiar (CSP/sanitizacao entram no hardening F8.14).
 */
'use client';

export interface AdminSession {
  accessToken: string;
  refreshToken: string;
  /** epoch ms em que o access token expira. */
  expiresAt: number;
}

const STORAGE_KEY = 'ecom.admin.session';

let memory: AdminSession | null = null;

function readStorage(): AdminSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AdminSession>;
    if (!parsed.accessToken || !parsed.refreshToken) return null;
    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
      expiresAt: typeof parsed.expiresAt === 'number' ? parsed.expiresAt : 0,
    };
  } catch {
    return null;
  }
}

export function getSession(): AdminSession | null {
  if (memory) return memory;
  memory = readStorage();
  return memory;
}

export function setSession(input: {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}): AdminSession {
  const session: AdminSession = {
    accessToken: input.access_token,
    refreshToken: input.refresh_token,
    expiresAt: Date.now() + input.expires_in * 1000,
  };
  memory = session;
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch {
      /* modo privado / quota — segue só com memória */
    }
  }
  return session;
}

export function clearSession(): void {
  memory = null;
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }
}

export function hasSession(): boolean {
  return getSession() !== null;
}

/** Considera "prestes a expirar" com 30s de folga. */
export function isAccessTokenStale(session: AdminSession): boolean {
  return Date.now() >= session.expiresAt - 30_000;
}
