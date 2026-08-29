import { API_BASE_URL } from './api-client';

/**
 * Normaliza URLs de mídia vindas da API.
 * - Absolutas (`http…`) passam direto.
 * - Relativas (`/media/…`) recebem o host da API na frente.
 * - Vazias devolvem `null` (o chamador decide o placeholder).
 */
export function resolveMediaUrl(url?: string | null): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;
}
