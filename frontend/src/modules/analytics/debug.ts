/**
 * Log de depuração dos eventos de analytics — só em desenvolvimento.
 * Ativa/desativa por `?analytics_debug=1` (persiste em sessionStorage) ou
 * automaticamente quando `NODE_ENV !== 'production'`.
 */
function enabled(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const q = new URLSearchParams(window.location.search);
    if (q.get('analytics_debug') === '1') sessionStorage.setItem('ecom:analytics_debug', '1');
    if (q.get('analytics_debug') === '0') sessionStorage.removeItem('ecom:analytics_debug');
    if (sessionStorage.getItem('ecom:analytics_debug') === '1') return true;
  } catch {
    /* noop */
  }
  return process.env.NODE_ENV !== 'production';
}

export function logEvent(event: string, payload?: unknown): void {
  if (!enabled()) return;
  // eslint-disable-next-line no-console
  console.debug(`%c[Analytics]%c ${event}`, 'color:#2563eb;font-weight:bold', 'color:inherit', payload ?? '');
}
