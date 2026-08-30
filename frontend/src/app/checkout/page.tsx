import type { Metadata } from 'next';
import { getTheme } from '@/modules/theme';
import { getProduct } from '@/modules/catalog/api';
import { CheckoutView, type OrderBumpProduct } from '@/components/checkout/checkout-view';
import { CheckoutHeader, CheckoutFooter } from '@/components/checkout/checkout-chrome';
import { CheckoutThemeStyle } from '@/components/checkout/checkout-theme-style';
import { buildMetadata, SITE_NAME } from '@/lib/seo';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = buildMetadata({
  title: 'Checkout',
  path: '/checkout',
  noindex: true,
});

async function loadOrderBump(slug: string | null): Promise<OrderBumpProduct | null> {
  if (!slug) return null;
  const p = await getProduct(slug).catch(() => null);
  if (!p) return null;
  const variant =
    p.variants.find((v) => v.is_active && v.in_stock) ?? p.variants.find((v) => v.is_active) ?? p.variants[0];
  const image = p.images.find((i) => i.is_primary) ?? p.images[0];
  return {
    slug: p.slug,
    name: p.name,
    price_cents: variant?.price_cents ?? p.price_cents,
    image_url: image?.medium_url ?? null,
    variant_id: variant?.id ?? null,
  };
}

export default async function CheckoutPage() {
  const theme = await getTheme();
  const orderBump =
    theme.checkout_orderbump_enabled && theme.checkout_orderbump_product_id
      ? await loadOrderBump(theme.checkout_orderbump_product_id)
      : null;

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
          orderBump={orderBump}
          settings={{
            emailFirst: theme.checkout_email_first,
            showCoupon: theme.checkout_show_coupon,
            itemsLayout: theme.checkout_items_layout,
            allowQtyChange: theme.checkout_allow_qty_change,
            buttonColor: theme.checkout_button_color,
            buttonTextColor: theme.checkout_button_text_color,
            animatedCard: theme.checkout_animated_card,
            showReview: theme.checkout_show_review,
            reviewPosition: theme.checkout_review_position,
          }}
        />
      </main>
      <CheckoutFooter theme={theme} />
    </div>
  );
}
