import type { Metadata } from 'next';
import { getTheme } from '@/modules/theme';
import { CheckoutView } from '@/components/checkout/checkout-view';
import { CheckoutHeader, CheckoutFooter } from '@/components/checkout/checkout-chrome';
import { CheckoutThemeStyle } from '@/components/checkout/checkout-theme-style';
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
    <div className="checkout-scope min-h-dvh bg-bg">
      <CheckoutThemeStyle theme={theme} />
      <CheckoutHeader theme={theme} storeName={SITE_NAME} />
      <main
        id="conteudo"
        className="mx-auto w-full px-4 py-6 sm:py-8"
        style={{ maxWidth: `${theme.checkout_container_width_px}px` }}
      >
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Finalizar compra</h1>
        <CheckoutView
          settings={{
            emailFirst: theme.checkout_email_first,
            showCoupon: theme.checkout_show_coupon,
            itemsLayout: theme.checkout_items_layout,
            allowQtyChange: theme.checkout_allow_qty_change,
            buttonColor: theme.checkout_button_color,
          }}
        />
      </main>
      <CheckoutFooter theme={theme} />
    </div>
  );
}
