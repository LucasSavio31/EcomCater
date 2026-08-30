import type { Metadata } from 'next';
import { getTheme } from '@/modules/theme';
import { CheckoutView } from '@/components/checkout/checkout-view';
import { CheckoutHeader, CheckoutFooter } from '@/components/checkout/checkout-chrome';
import { buildMetadata, SITE_NAME } from '@/lib/seo';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = buildMetadata({
  title: 'Checkout',
  path: '/checkout',
  noindex: true,
});

export default async function CheckoutPage() {
  const theme = await getTheme();
  return (
    <div className="min-h-dvh bg-bg">
      <CheckoutHeader theme={theme} storeName={SITE_NAME} />
      <main id="conteudo" className="mx-auto w-full max-w-5xl px-4 py-6 sm:py-8">
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Finalizar compra</h1>
        <CheckoutView />
      </main>
      <CheckoutFooter theme={theme} />
    </div>
  );
}
