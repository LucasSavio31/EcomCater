import type { Metadata, Viewport } from 'next';
import { Suspense } from 'react';
import './globals.css';
import { getTheme, ThemeStyle } from '@/modules/theme';
import { getMenu } from '@/modules/menus/api';
import { getAnalyticsConfig } from '@/modules/analytics/get-config';
import { AnalyticsHeadScripts, AnalyticsBodyNoScript } from '@/modules/analytics/scripts';
import { AnalyticsRouteTracker } from '@/modules/analytics/route-tracker';
import { AnalyticsIdentity } from '@/components/analytics/analytics-identity';
import { ServiceWorker } from '@/components/service-worker';
import { ScrollToTop } from '@/components/scroll-to-top';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteFooter } from '@/components/layout/site-footer';
import { StorefrontShell } from '@/components/layout/storefront-shell';
import { CookieConsent } from '@/components/layout/cookie-consent';
import { LeadPopupAuto } from '@/components/lead-popup-auto';
import { CartProvider } from '@/modules/cart/cart-context';
import { MiniCartDrawer } from '@/components/cart/mini-cart-drawer';
import { AuthProvider } from '@/modules/customer/auth-context';
import { SITE_NAME, SITE_URL, jsonLdScript, organizationJsonLd, webSiteJsonLd } from '@/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const theme = await getTheme();
  const favicon = theme.favicon_url || '/icons/icon-192.png';
  return {
    metadataBase: new URL(SITE_URL),
    title: { default: SITE_NAME, template: `%s · ${SITE_NAME}` },
    description: 'Loja online.',
    manifest: '/manifest.json',
    applicationName: SITE_NAME,
    icons: {
      icon: favicon,
      shortcut: favicon,
      apple: theme.favicon_url || '/icons/icon-192.png',
    },
  };
}

export const viewport: Viewport = {
  themeColor: '#111111',
  width: 'device-width',
  initialScale: 1,
  // Sem zoom no mobile. (O iOS ainda pode permitir pinça por acessibilidade;
  // o que trava mesmo o "zoom ao focar campo" é a regra de fonte 16px no CSS.)
  maximumScale: 1,
  userScalable: false,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const [theme, headerMenu, footerMenu, analytics] = await Promise.all([
    getTheme(),
    getMenu('header'),
    getMenu('footer'),
    getAnalyticsConfig(),
  ]);

  const orgLd = jsonLdScript([organizationJsonLd({ logoUrl: theme.logo_url ?? undefined }), webSiteJsonLd()]);

  return (
    // suppressHydrationWarning: extensões (Google Tag Assistant etc.) injetam
    // atributos em <html>/<body> antes do React hidratar.
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-dvh bg-bg text-text" suppressHydrationWarning>
        {/* Tags de marketing (GTM / GA4 / Google Ads / Meta Pixel) o mais alto possível. */}
        <AnalyticsHeadScripts config={analytics} />
        <AnalyticsBodyNoScript config={analytics} />
        <Suspense fallback={null}>
          <AnalyticsRouteTracker />
        </Suspense>
        <AnalyticsIdentity />
        <ScrollToTop />

        {/* CSS vars do tema — antes do primeiro paint (sem FOUC). */}
        <ThemeStyle theme={theme} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: orgLd }} />

        <a href="#conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
          Pular para o conteúdo
        </a>

        <AuthProvider>
          <CartProvider>
            <StorefrontShell
              header={<SiteHeader theme={theme} menu={headerMenu} storeName={SITE_NAME} />}
              footer={<SiteFooter theme={theme} menu={footerMenu} storeName={SITE_NAME} />}
            >
              {children}
            </StorefrontShell>
            <MiniCartDrawer />
          </CartProvider>
        </AuthProvider>

        <CookieConsent
          enabled={theme.cookie_consent_enabled}
          text={theme.cookie_consent_text}
        />
        <LeadPopupAuto
          config={{
            enabled: theme.lead_popup_enabled,
            title: theme.lead_popup_title,
            subtitle: theme.lead_popup_subtitle,
            logoUrl: theme.lead_popup_show_logo
              ? theme.lead_popup_logo_url || theme.logo_url || null
              : null,
            bg: theme.lead_popup_bg_color,
            text: theme.lead_popup_text_color,
            btn: theme.lead_popup_button_color,
            btnText: theme.lead_popup_button_text_color,
          }}
        />
        <ServiceWorker />
      </body>
    </html>
  );
}
