import type { Metadata } from 'next';
import { Suspense } from 'react';
import { Spinner } from '@ecom/ui';
import { ThankYouView } from '@/components/checkout/thank-you-view';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  title: 'Pedido recebido',
  path: '/checkout/obrigado',
  noindex: true,
});

export default function CheckoutObrigadoPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold sm:text-2xl">Obrigado pela compra!</h1>
      <Suspense
        fallback={
          <p className="flex items-center gap-2 py-16 text-text-muted">
            <Spinner /> Carregando…
          </p>
        }
      >
        <ThankYouView />
      </Suspense>
    </div>
  );
}
