import { apiFetch } from '@/lib/api-client';
import type { Banner } from './types';

/** Banners de um slot, já ordenados por `position`. Degrada para `[]`. */
export async function getBanners(slot: 'hero' | 'showcase'): Promise<Banner[]> {
  const res = await apiFetch<Banner[]>('/api/banners', {
    query: { slot },
    next: { tags: ['banners', `banners:${slot}`], revalidate: 300 },
  });
  if (!res.ok) return [];
  return [...res.data].sort((a, b) => a.position - b.position);
}
