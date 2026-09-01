import type { ThemeSettings } from './types';

/** Mapeia o tema do banco para as CSS variables consumidas pelo preset Tailwind. */
export function themeToCssVars(theme: ThemeSettings): Record<string, string> {
  return {
    '--color-primary': theme.primary_color,
    '--color-secondary': theme.secondary_color,
    '--color-accent': theme.accent_color,
    '--color-text': theme.text_color,
    '--color-bg': theme.bg_color,
    '--color-surface': theme.bg_color,
    '--color-btn-bg': theme.button_bg_color,
    '--color-btn-fg': theme.button_text_color,
    '--color-btn-hover': theme.button_hover_color,
    '--color-var-bg': theme.variation_bg_color,
    '--color-var-fg': theme.variation_text_color,
    '--color-var-border': theme.variation_border_color,
    '--color-header-bg': theme.header_bg_color,
    '--color-header-fg': theme.header_text_color,
    '--color-footer-bg': theme.footer_bg_color,
    '--color-footer-fg': theme.footer_text_color,
    '--header-max-width': `${theme.header_max_width_px}px`,
    '--radius-btn': `${theme.button_radius_px ?? 12}px`,
    '--radius-var': `${theme.variation_radius_px ?? 12}px`,
    '--color-freight-bg': theme.freight_button_bg_color,
    '--color-freight-fg': theme.freight_button_text_color,
    '--color-freight-hover': theme.freight_button_hover_color,
    '--color-freight-border': theme.freight_button_border_color,
    '--radius-freight': `${theme.freight_button_radius_px ?? 12}px`,
    '--color-promo-bg': theme.promo_badge_bg_color,
    '--color-promo-fg': theme.promo_badge_text_color,
    '--color-promo-border': theme.promo_badge_border_color,
    '--radius-promo': `${theme.promo_badge_radius_px ?? 6}px`,
    '--color-cart-btn-bg': theme.cart_checkout_btn_bg_color,
    '--color-cart-btn-fg': theme.cart_checkout_btn_text_color,
    '--color-cart-btn-hover': theme.cart_checkout_btn_hover_color,
    '--color-cart-btn-border': theme.cart_checkout_btn_border_color,
    '--radius-cart-btn': `${theme.cart_checkout_btn_radius_px ?? 12}px`,
    '--color-cart-freight-bg': theme.cart_freight_btn_bg_color,
    '--color-cart-freight-fg': theme.cart_freight_btn_text_color,
    '--color-cart-freight-hover': theme.cart_freight_btn_hover_color,
    '--color-cart-freight-border': theme.cart_freight_btn_border_color,
    '--radius-cart-freight': `${theme.cart_freight_btn_radius_px ?? 12}px`,
    '--color-cart-qty-bg': theme.cart_qty_bg_color,
    '--color-cart-qty-fg': theme.cart_qty_text_color,
    '--radius-cart-qty': `${theme.cart_qty_radius_px ?? 12}px`,
    '--color-cart-coupon-bg': theme.cart_coupon_btn_bg_color,
    '--color-cart-coupon-fg': theme.cart_coupon_btn_text_color,
    '--color-cart-coupon-hover': theme.cart_coupon_btn_hover_color,
    '--color-cart-coupon-border': theme.cart_coupon_btn_border_color,
    '--radius-cart-coupon': `${theme.cart_coupon_btn_radius_px ?? 12}px`,
    '--color-cart-badge-bg': theme.cart_badge_bg_color,
    '--color-cart-badge-fg': theme.cart_badge_text_color,
    '--color-wish-bg': theme.pdp_wishlist_bg_color,
    '--color-wish-border': theme.pdp_wishlist_border_color,
    '--color-wish-icon': theme.pdp_wishlist_icon_color,
    '--font-family': theme.font_family,
  };
}

function serialize(vars: Record<string, string>): string {
  const body = Object.entries(vars)
    .map(([k, v]) => `${k}:${String(v).replace(/[<>]/g, '')};`)
    .join('');
  return `:root{${body}}`;
}

/**
 * `<style>` inline com as CSS vars do tema. Renderizado como primeiro nó do
 * <body> no SSR — entra no HTML inicial, aplicado antes do primeiro paint
 * (sem FOUC) e sem custo de rede.
 */
export function ThemeStyle({ theme }: { theme: ThemeSettings }) {
  let css = serialize(themeToCssVars(theme));
  if (!theme.discount_badge_enabled) {
    css += '.ecom-discount-badge{display:none !important;}';
  } else {
    // selo de promoção (-XX%) usa as cores configuradas — só quando tem fundo (card/PDP)
    css +=
      '.ecom-discount-badge.ecom-promo-pill{background:var(--color-promo-bg) !important;' +
      'color:var(--color-promo-fg) !important;' +
      'border:1px solid var(--color-promo-border) !important;' +
      'border-radius:var(--radius-promo) !important;}';
    // liga/desliga o selo por superfície
    if (!theme.promo_badge_card_enabled) {
      css += '.ecom-promo-pill--card{display:none !important;}';
    }
    if (!theme.promo_badge_pdp_enabled) {
      css += '.ecom-promo-pill--pdp{display:none !important;}';
    }
  }
  if (theme.card_hover_zoom_enabled) {
    css +=
      '.ecom-card-img{transition:transform .6s ease}' +
      '.group:hover .ecom-card-img{transform:scale(1.045)}';
  }
  return (
    <style
      id="ecom-theme"
      // CSS estático derivado do tema; sanitizado contra `<` / `>`.
      dangerouslySetInnerHTML={{ __html: css }}
    />
  );
}
