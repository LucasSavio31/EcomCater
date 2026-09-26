import type { MetadataRoute } from 'next';
import { resolveSite } from '@/lib/seo';
import { siteOrigin } from '@/lib/site';
import { getAnalyticsConfig } from '@/modules/analytics/get-config';

// Por domínio (multi-domínio): sitemap/host do próprio domínio, e bloqueio
// total se ele estiver marcado "não indexar" em Rastreamento.
export default async function robots(): Promise<MetadataRoute.Robots> {
  const site = await resolveSite();
  const siteUrl = siteOrigin(site);
  const cfg = await getAnalyticsConfig(site);
  if (cfg.seo_noindex) {
    return { rules: { userAgent: '*', disallow: '/' } };
  }
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/carrinho', '/checkout', '/minha-conta', '/busca'],
    },
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
