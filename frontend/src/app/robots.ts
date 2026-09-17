import type { MetadataRoute } from 'next';
import { resolveSiteUrl } from '@/lib/seo';

export default async function robots(): Promise<MetadataRoute.Robots> {
  const siteUrl = await resolveSiteUrl();
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
