import type { Metadata, Viewport } from 'next';
import { Suspense } from 'react';
import '../globals.css';
import { getTheme, ThemeStyle } from '@/modules/theme';
import { getMenu } from '@/modules/menus/api';
import { getAnalyticsConfig } from '@/modules/analytics/get-config';
import { AnalyticsHeadScripts, AnalyticsBodyNoScript } from '@/modules/analytics/scripts';
import { AnalyticsRouteTracker } from '@/modules/analytics/route-tracker';
import { AnalyticsIdentity } from '@/components/analytics/analytics-identity';
import { ServiceWorker } from '@/components/service-worker';
import { PresenceBeacon } from '@/components/presence-beacon';
import { ScrollToTop } from '@/components/scroll-to-top';
import { PdpContextGuard } from '@/components/pdp/pdp-context-guard';
import { SiteHeader } from '@/components/layout/site-header';
import { SiteFooter } from '@/components/layout/site-footer';
import { StorefrontShell } from '@/components/layout/storefront-shell';
import { CookieConsent } from '@/components/layout/cookie-consent';
import { LeadPopupAuto } from '@/components/lead-popup-auto';
import { CartProvider } from '@/modules/cart/cart-context';
import { MiniCartDrawer } from '@/components/cart/mini-cart-drawer';
import { AuthProvider } from '@/modules/customer/auth-context';
import { SITE_NAME, jsonLdScript, organizationJsonLd, webSiteJsonLd } from '@/lib/seo';
import { API_BASE_URL } from '@/lib/api-client';
import { DEFAULT_SITE, siteApiOrigin, siteOrigin } from '@/lib/site';

// Layout RAIZ de cada domínio (multi-domínio): o middleware reescreve
// `/<rota>` pra `/<site>/<rota>`, então cada domínio tem o próprio cache de
// página, `metadataBase` (canonical/OG absolutos), tags e SEO.
interface LayoutParams {
  params: Promise<{ site: string }>;
}

// Com o segmento dinâmico [site], sem isto o Next montaria TODA página a cada
// request (sem ISR). O domínio padrão é pré-gerado no build; os outros entram
// no cache na 1ª visita (dynamicParams).
export function generateStaticParams(): { site: string }[] {
  return [{ site: DEFAULT_SITE }];
}

export async function generateMetadata({ params }: LayoutParams): Promise<Metadata> {
  const { site } = await params;
  const [theme, cfg] = await Promise.all([getTheme(), getAnalyticsConfig(site)]);
  const favicon = theme.favicon_url || '/icons/icon-192.png';
  const name = theme.store_name?.trim() || SITE_NAME;
  return {
    metadataBase: new URL(siteOrigin(site)),
    title: { default: cfg.seo_title?.trim() || name, template: `%s · ${name}` },
    description: cfg.seo_description || 'Loja online.',
    // domínio marcado "não indexar" (o middleware também manda X-Robots-Tag)
    ...(cfg.seo_noindex ? { robots: { index: false, follow: false } } : {}),
    manifest: '/manifest.webmanifest',
    applicationName: name,
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
  params,
}: Readonly<{ children: React.ReactNode; params: Promise<{ site: string }> }>) {
  const { site } = await params;
  const [theme, headerMenu, footerMenu, analytics] = await Promise.all([
    getTheme(),
    getMenu('header'),
    getMenu('footer'),
    // só as tags DESTE domínio (pixel/GTM/GA4/Ads/Merchant são por domínio)
    getAnalyticsConfig(site),
  ]);

  const origin = siteOrigin(site);
  const orgLd = jsonLdScript([
    organizationJsonLd({ logoUrl: theme.logo_url ?? undefined, name: theme.store_name, url: origin }),
    webSiteJsonLd(theme.store_name, origin),
  ]);
  // Origem da API do domínio (o navegador fala com api.<site>): abrir a
  // conexão TLS cedo economiza o RTT do primeiro request de JSON.
  const API_ORIGIN = (() => {
    try {
      return new URL(siteApiOrigin(site, API_BASE_URL)).origin;
    } catch {
      return '';
    }
  })();

  return (
    // suppressHydrationWarning: extensões (Google Tag Assistant etc.) injetam
    // atributos em <html>/<body> antes do React hidratar.
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-dvh bg-bg text-text" suppressHydrationWarning>
        {API_ORIGIN && (
          <>
            <link rel="preconnect" href={API_ORIGIN} crossOrigin="anonymous" />
            <link rel="dns-prefetch" href={API_ORIGIN} />
          </>
        )}
        {/* Google Merchant Center — comprova a propriedade do site. Renderizada
            direto (não via generateMetadata) porque o Next hoisteia pro <head>
            de qualquer jeito, e assim fica no mesmo lugar/padrão do resto das
            tags de marketing abaixo. */}
        {analytics.merchant_center_enabled && analytics.merchant_center_verification_code && (
          <meta
            name="google-site-verification"
            content={analytics.merchant_center_verification_code}
          />
        )}
        {/* CSS vars do tema — precisa vir antes de qualquer <script src> bloqueante
            (GTM/gtag/Pixel abaixo), senão o parser trava nesses scripts e pinta
            o body com as cores padrão do navegador antes de chegar aqui (FOUC). */}
        <ThemeStyle theme={theme} />

        {/* Tags de marketing (GTM / GA4 / Google Ads / Meta Pixel) o mais alto possível. */}
        <AnalyticsHeadScripts config={analytics} />
        <AnalyticsBodyNoScript config={analytics} />
        <Suspense fallback={null}>
          <AnalyticsRouteTracker />
        </Suspense>
        <AnalyticsIdentity />
        <ScrollToTop />
        <PdpContextGuard />
        <PresenceBeacon />

        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: orgLd }} />

        <a href="#conteudo" className="skip-link rounded-card bg-primary px-3 py-2 text-primary-fg">
          Pular para o conteúdo
        </a>

        <AuthProvider>
          <CartProvider>
            <StorefrontShell
              header={<SiteHeader theme={theme} menu={headerMenu} storeName={theme.store_name ?? SITE_NAME} />}
              footer={<SiteFooter theme={theme} menu={footerMenu} storeName={theme.store_name ?? SITE_NAME} />}
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
