import 'server-only';
import { apiFetch } from '@/lib/api-client';
import { NEUTRAL_THEME, type ThemeSettings } from './types';

/**
 * Busca o tema no servidor. Cacheado e marcado com a tag `theme` para o admin
 * poder revalidar sob demanda (`revalidateTag('theme')`) sem rebuild.
 *
 * Nunca lança: se a API estiver fora (ex.: durante `next build`), devolve a
 * paleta neutra — a loja sobe mesmo assim.
 */
export async function getTheme(): Promise<ThemeSettings> {
  const result = await apiFetch<ThemeSettings>('/api/theme', {
    next: { tags: ['theme'], revalidate: 60 },
  });
  if (!result.ok) return NEUTRAL_THEME;
  return { ...NEUTRAL_THEME, ...result.data };
}
