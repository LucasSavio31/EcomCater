/* eslint-disable @next/next/no-before-interactive-script-outside-document --
   App Router: `beforeInteractive` no layout raiz é o lugar correto para tags de
   marketing (GTM/gtag/Pixel) irem para o `<head>`. Não existe `_document`. */
import Script from 'next/script';
import type { AnalyticsConfig } from './types';

/**
 * Tags de marketing injetadas o mais alto possível no `<head>` (SSR), como
 * exigem a documentação do Google Tag Manager, do Google (gtag.js) e do
 * Meta Pixel. `strategy="beforeInteractive"` só é permitido no layout raiz —
 * é exatamente onde este componente é usado.
 *
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
      <Script id="ecom-analytics-bootstrap" strategy="beforeInteractive">
        {bootstrap}
      </Script>

      {gtm && (
        <Script id="gtm" strategy="beforeInteractive">
          {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','${gtm}');`}
        </Script>
      )}

      {gtagPrimary && (
        <>
          <Script
            id="gtag-src"
            strategy="beforeInteractive"
            src={`https://www.googletagmanager.com/gtag/js?id=${gtagPrimary}`}
          />
          <Script id="gtag-init" strategy="beforeInteractive">
            {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}window.gtag=window.gtag||gtag;gtag('js',new Date());${
              ga4 ? `gtag('config','${ga4}');` : ''
            }${ads ? `gtag('config','${ads}');` : ''}`}
          </Script>
        </>
      )}

      {pixel && (
        <Script id="meta-pixel" strategy="beforeInteractive">
          {`!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','${pixel}');fbq('track','PageView');`}
        </Script>
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
