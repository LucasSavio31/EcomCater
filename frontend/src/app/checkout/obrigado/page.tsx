import type { Metadata } from 'next';
import { Suspense } from 'react';
import { Spinner } from '@ecom/ui';
import { getTheme } from '@/modules/theme';
import { ThankYouView } from '@/components/checkout/thank-you-view';
import { CheckoutHeader, CheckoutFooter } from '@/components/checkout/checkout-chrome';
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
    <div className="min-h-dvh bg-bg">
      <CheckoutHeader theme={theme} storeName={SITE_NAME} />
      <main id="conteudo" className="mx-auto w-full max-w-3xl px-4 py-8">
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
      <CheckoutFooter theme={theme} />
    </div>
  );
}
