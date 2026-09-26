/**
 * Multi-domínio: a mesma loja em vários domínios, cada um com as próprias
 * páginas/cache/SEO/tags. O middleware reescreve `/<rota>` pra
 * `/<site>/<rota>` (segmento `app/[site]`), então cada domínio tem o próprio
 * cache de página (ISR) — canonical, JSON-LD e tags nunca vazam de um
 * domínio pro outro.
 *
 * `site` = hostname da loja, sem `www.`/porta (ex.: `loja-b.com.br`). O
 * domínio do build (`NEXT_PUBLIC_SITE_URL`) é o `DEFAULT_SITE` — também é o
 * que atende IP, localhost e qualquer host desconhecido.
 */

export const SITE_URL: string = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

export function normalizeHost(raw: string | null | undefined): string {
  if (!raw) return '';
  let h = raw.split(',')[0]!.trim().toLowerCase();
  if (h.includes('://')) {
    try {
      h = new URL(h).hostname;
    } catch {
      return '';
    }
  }
  h = h.replace(/:\d+$/, '').replace(/\.$/, '');
  return h.startsWith('www.') ? h.slice(4) : h;
}

export const DEFAULT_SITE: string = normalizeHost(SITE_URL) || 'localhost';

/** Origem pública da loja do `site` (sem barra no fim). */
export function siteOrigin(site: string | null | undefined): string {
  const s = normalizeHost(site);
  if (!s || s === DEFAULT_SITE) return SITE_URL.replace(/\/$/, '');
  return `https://${s}`;
}

/** Origem pública da API do `site` (`api.<site>`, criada em Infraestrutura). */
export function siteApiOrigin(site: string | null | undefined, fallback: string): string {
  const s = normalizeHost(site);
  if (!s || s === DEFAULT_SITE) return fallback.replace(/\/$/, '');
  return `https://api.${s}`;
}
