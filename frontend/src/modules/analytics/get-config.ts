import 'server-only';
import { apiFetch } from '@/lib/api-client';
import { DISABLED_ANALYTICS, type AnalyticsConfig } from './types';

/**
 * Busca a config de rastreamento/SEO do domínio `site` no servidor — cada
 * domínio tem as próprias tags (multi-domínio). Cacheada com a tag
 * `analytics` (o admin revalida ao salvar). Nunca lança: se a API estiver
 * fora, devolve tudo desabilitado — nenhuma tag é injetada.
 */
export async function getAnalyticsConfig(site?: string): Promise<AnalyticsConfig> {
  const res = await apiFetch<AnalyticsConfig>('/api/analytics/config', {
    query: site ? { site } : undefined,
    next: { tags: ['analytics'], revalidate: 300 },
  });
  if (!res.ok) return DISABLED_ANALYTICS;
  return { ...DISABLED_ANALYTICS, ...res.data };
}
