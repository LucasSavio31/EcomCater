import type { ThemeSettings } from '@/modules/theme';

/**
 * Sobrescreve, **apenas dentro de `.checkout-scope`**, as CSS vars do design
 * system com as cores próprias do checkout (menu "Checkout" no admin). Assim
 * todos os componentes existentes (`bg-btn`, `text-primary`, `bg-header`…)
 * passam a usar as cores do checkout sem precisar mexer em cada um.
 */
function sanitize(v: string): string {
  return String(v).replace(/[<>"'{}]/g, '');
}

export function CheckoutThemeStyle({ theme }: { theme: ThemeSettings }) {
  const vars: Record<string, string> = {
    '--color-bg': theme.checkout_bg_color,
    '--color-bg-subtle': theme.checkout_bg_color,
    '--color-btn-bg': theme.checkout_button_color,
    '--color-btn-fg': theme.checkout_button_text_color,
    '--color-btn-hover': theme.checkout_button_color,
    '--color-primary': theme.checkout_accent_color,
    '--color-primary-fg': theme.checkout_button_text_color,
    '--color-accent': theme.checkout_accent_color,
    '--color-header-bg': theme.checkout_header_bg_color,
    '--color-header-fg': theme.checkout_header_text_color,
    '--color-footer-bg': theme.checkout_footer_bg_color,
    '--color-footer-fg': theme.checkout_footer_text_color,
  };
  const css = `.checkout-scope{${Object.entries(vars)
    .map(([k, v]) => `${k}:${sanitize(v)}`)
    .join(';')}}`;
  return <style id="ecom-checkout-theme" dangerouslySetInnerHTML={{ __html: css }} />;
}
