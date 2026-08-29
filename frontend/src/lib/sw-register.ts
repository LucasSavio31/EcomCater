/**
 * Registro do service worker da loja (cache básico de assets estáticos).
 * Sem estratégia offline completa — só acelera navegações repetidas.
 */
export function registerServiceWorker(): void {
  if (typeof window === 'undefined') return;
  if (!('serviceWorker' in navigator)) return;
  if (process.env.NODE_ENV !== 'production') return;

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* registro é best-effort; falha não afeta a loja */
    });
  });
}
