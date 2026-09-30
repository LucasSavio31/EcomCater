import Script from 'next/script';
import type { AnalyticsConfig } from './types';

/**
 * Tags de marketing (GTM/gtag/Pixel) em duas partes, pra nunca travar a loja:
 *
 * 1. Fila (`dataLayer`, `gtag()`, `fbq()`) — snippet inline minúsculo, sem
 *    rede, `afterInteractive`. O tracker já pode empurrar eventos desde a
 *    hidratação; nada se perde.
 * 2. Biblioteca do fornecedor (`gtm.js`, `gtag/js`, `fbevents.js`, ~100 KB+
 *    cada, com execução pesada) — `lazyOnload`: só baixa depois do `onload`,
 *    com o navegador ocioso. Ao carregar, processa a fila acumulada. Assim
 *    ela não disputa banda com a imagem principal (LCP) nem trava a thread
 *    principal nos primeiros toques do cliente (INP).
 *
 * Nunca `beforeInteractive` (bloqueia a hidratação — achado do PageSpeed).
 * Nada é renderizado quando a integração está desligada no admin.
 */
export function AnalyticsHeadScripts({ config }: { config: AnalyticsConfig }) {
  const gtm = config.gtm_enabled && config.gtm_container_id ? config.gtm_container_id : null;
  const ga4 = config.ga4_enabled && config.ga4_measurement_id ? config.ga4_measurement_id : null;
  const ads =
    config.google_ads_enabled && config.google_ads_conversion_id
      ? config.google_ads_conversion_id
      : null;
  const pixel = config.meta_pixel_enabled && config.meta_pixel_id ? config.meta_pixel_id : null;
  const gtagPrimary = ga4 ?? ads;

  // exposto para o tracker do cliente (conversão do Google Ads precisa do label)
  const bootstrap = `window.__ECOM_ANALYTICS__=${JSON.stringify({
    ga4,
    ads,
    adsPurchaseLabel: config.google_ads_purchase_label ?? null,
    pixel,
    gtm,
  })};`;

  return (
    <>
      <Script id="ecom-analytics-bootstrap" strategy="afterInteractive">
        {bootstrap}
      </Script>

      {gtm && (
        <>
          <Script id="gtm" strategy="afterInteractive">
            {`window.dataLayer=window.dataLayer||[];window.dataLayer.push({'gtm.start':new Date().getTime(),event:'gtm.js'});`}
          </Script>
          <Script
            id="gtm-src"
            strategy="lazyOnload"
            src={`https://www.googletagmanager.com/gtm.js?id=${gtm}`}
          />
        </>
      )}

      {gtagPrimary && (
        <>
          <Script
            id="gtag-src"
            strategy="lazyOnload"
            src={`https://www.googletagmanager.com/gtag/js?id=${gtagPrimary}`}
          />
          <Script id="gtag-init" strategy="afterInteractive">
            {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}window.gtag=window.gtag||gtag;gtag('js',new Date());${
              ga4 ? `gtag('config','${ga4}');` : ''
            }${ads ? `gtag('config','${ads}');` : ''}`}
          </Script>
        </>
      )}

      {pixel && (
        <>
          {/* snippet oficial do Pixel sem o trecho que injeta o fbevents.js */}
          <Script id="meta-pixel" strategy="afterInteractive">
            {`!function(f){if(f.fbq)return;var n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[]}(window);fbq('init','${pixel}');fbq('track','PageView');`}
          </Script>
          <Script
            id="meta-pixel-src"
            strategy="lazyOnload"
            src="https://connect.facebook.net/en_US/fbevents.js"
          />
        </>
      )}
    </>
  );
}

/** `<noscript>` do GTM — vai logo após a abertura do `<body>`. */
export function AnalyticsBodyNoScript({ config }: { config: AnalyticsConfig }) {
  const gtm = config.gtm_enabled && config.gtm_container_id ? config.gtm_container_id : null;
  const pixel = config.meta_pixel_enabled && config.meta_pixel_id ? config.meta_pixel_id : null;
  if (!gtm && !pixel) return null;
  return (
    <>
      {gtm && (
        <noscript>
          <iframe
            src={`https://www.googletagmanager.com/ns.html?id=${gtm}`}
            height="0"
            width="0"
            style={{ display: 'none', visibility: 'hidden' }}
            title="gtm"
          />
        </noscript>
      )}
      {pixel && (
        <noscript>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            height="1"
            width="1"
            style={{ display: 'none' }}
            alt=""
            src={`https://www.facebook.com/tr?id=${pixel}&ev=PageView&noscript=1`}
          />
        </noscript>
      )}
    </>
  );
}
