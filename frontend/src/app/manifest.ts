import type { MetadataRoute } from 'next';
import { getTheme } from '@/modules/theme';

export const revalidate = 300;

export default async function manifest(): Promise<MetadataRoute.Manifest> {
  const theme = await getTheme().catch(() => null);
  const name = theme?.store_name?.trim() || 'Loja';
  return {
    name,
    short_name: name,
    description: name,
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    lang: 'pt-BR',
    dir: 'ltr',
    background_color: '#ffffff',
    theme_color: '#111111',
    icons: [
      { src: theme?.favicon_url || '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
