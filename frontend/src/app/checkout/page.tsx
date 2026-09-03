import type { Metadata } from 'next';
import { getTheme } from '@/modules/theme';
import { getProduct } from '@/modules/catalog/api';
import { CheckoutView, type OrderBumpProduct } from '@/components/checkout/checkout-view';
import { CheckoutHeader } from '@/components/checkout/checkout-chrome';
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

  const bumpSlugs = theme.checkout_orderbump_enabled
    ? (() => {
        const list = theme.checkout_orderbump_product_ids ?? [];
        if (list.length > 0) return list;
        return theme.checkout_orderbump_product_id ? [theme.checkout_orderbump_product_id] : [];
      })()
    : [];
  const orderBumps = (await Promise.all(bumpSlugs.map((s) => loadOrderBump(s)))).filter(
    (b): b is OrderBumpProduct => b !== null,
  );

  return (
    <div className="checkout-scope min-h-dvh bg-bg">
      <CheckoutThemeStyle theme={theme} />
      <CheckoutHeader theme={theme} storeName={theme.store_name ?? SITE_NAME} />
      <main
        id="conteudo"
        className="mx-auto w-full px-4 py-6 sm:py-8"
        style={{ maxWidth: `${theme.checkout_container_width_px}px` }}
      >
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Finalizar Compra</h1>
        <CheckoutView
          orderBumps={orderBumps}
          settings={{
            emailFirst: theme.checkout_email_first,
            requireTerms: theme.checkout_require_terms,
            showCoupon: theme.checkout_show_coupon,
            itemsLayout: theme.checkout_items_layout,
            allowQtyChange: theme.checkout_allow_qty_change,
            buttonColor: theme.checkout_button_color,
            buttonTextColor: theme.checkout_button_text_color,
            stepActiveBg: theme.checkout_step_active_bg_color,
            stepActiveText: theme.checkout_step_active_text_color,
            animatedCard: theme.checkout_animated_card,
            paymentIcons: theme.checkout_payment_icons_enabled,
            stepsTimeline: theme.checkout_steps_enabled,
            showReview: theme.checkout_show_review,
            reviewPosition: theme.checkout_review_position,
            orderNotes: theme.checkout_order_notes_enabled,
          }}
        />
      </main>
    </div>
  );
}
