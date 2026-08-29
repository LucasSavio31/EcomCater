import type { MetadataRoute } from 'next';
import { SITE_URL } from '@/lib/seo';

/**
 * Sitemap base (Fase 1) — só as rotas estáticas indexáveis.
 * Categorias/produtos/páginas dinâmicas entram na Fase 3 (F3.10).
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: 'daily', priority: 1 },
  ];
}
