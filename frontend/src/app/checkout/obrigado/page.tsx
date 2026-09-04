import type { Metadata } from 'next';
import { Suspense } from 'react';
import { Spinner } from '@ecom/ui';
import { getTheme } from '@/modules/theme';
import { ThankYouView } from '@/components/checkout/thank-you-view';
import { CheckoutFooter, CheckoutHeader } from '@/components/checkout/checkout-chrome';
import { CheckoutThemeStyle } from '@/components/checkout/checkout-theme-style';
import { buildMetadata, SITE_NAME } from '@/lib/seo';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = buildMetadata({
  title: 'Pedido recebido',
  path: '/checkout/obrigado',
  noindex: true,
});

export default async function CheckoutObrigadoPage() {
  const theme = await getTheme();
  return (
    <div className="checkout-scope flex min-h-dvh flex-col bg-bg">
      <CheckoutThemeStyle theme={theme} />
      <CheckoutHeader theme={theme} storeName={theme.store_name ?? SITE_NAME} />
      <main id="conteudo" className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Obrigado pela compra!</h1>
        <Suspense
          fallback={
            <p className="flex items-center gap-2 py-16 text-text-muted">
              <Spinner /> Carregando…
            </p>
          }
        >
          <ThankYouView />
        </Suspense>
      </main>
      <CheckoutFooter theme={theme} storeName={theme.store_name ?? SITE_NAME} />
    </div>
  );
}
