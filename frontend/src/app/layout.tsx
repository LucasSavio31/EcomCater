import type { Metadata, Viewport } from 'next';
import './globals.css';
import { getTheme, ThemeStyle } from '@/modules/theme';
import { getMenu } from '@/modules/menus/api';
import { ServiceWorker } from '@/components/service-worker';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteFooter } from '@/components/layout/site-footer';
import { CartProvider } from '@/modules/cart/cart-context';
import { SITE_NAME, SITE_URL, jsonLdScript, organizationJsonLd, webSiteJsonLd } from '@/lib/seo';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE_NAME, template: `%s · ${SITE_NAME}` },
  description: 'Loja online.',
  manifest: '/manifest.json',
  applicationName: SITE_NAME,
  icons: {
    icon: '/icons/icon-192.png',
    apple: '/icons/icon-192.png',
  },
};

export const viewport: Viewport = {
  themeColor: '#111111',
  width: 'device-width',
  initialScale: 1,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const [theme, headerMenu, footerMenu] = await Promise.all([
    getTheme(),
    getMenu('header'),
    getMenu('footer'),
  ]);

  const orgLd = jsonLdScript([organizationJsonLd({ logoUrl: theme.logo_url ?? undefined }), webSiteJsonLd()]);

  return (
    <html lang="pt-BR">
      <body className="min-h-dvh bg-bg text-text">
        {/* CSS vars do tema — antes do primeiro paint (sem FOUC). */}
        <ThemeStyle theme={theme} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: orgLd }} />

        <a href="#conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
          Pular para o conteúdo
        </a>

        <CartProvider>
          <SiteHeader theme={theme} menu={headerMenu} storeName={SITE_NAME} />

          <main id="conteudo" className="mx-auto w-full max-w-6xl px-4 py-6 sm:py-8">
            {children}
          </main>

          <SiteFooter theme={theme} menu={footerMenu} storeName={SITE_NAME} />
        </CartProvider>

        <ServiceWorker />
      </body>
    </html>
  );
}
