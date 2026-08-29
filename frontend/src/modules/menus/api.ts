import { apiFetch } from '@/lib/api-client';
import type { Menu } from './types';

/**
 * Menu por localização. A API devolve uma lista de menus da localização;
 * pegamos o primeiro (há 1 menu ativo por local). Degrada para `null`.
 */
export async function getMenu(location: 'header' | 'footer'): Promise<Menu | null> {
  const res = await apiFetch<Menu[]>(`/api/menus/${location}`, {
    next: { tags: ['menus', `menu:${location}`], revalidate: 300 },
  });
  if (!res.ok || res.data.length === 0) return null;
  return res.data[0] ?? null;
}
