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
  // Os botões de etapa ("Avançar", "Calcular frete") usam --color-btn-*.
  // O botão de finalizar e a bolinha da etapa ativa recebem cor inline.
  const vars: Record<string, string> = {
    '--color-bg': theme.checkout_bg_color,
    '--color-bg-subtle': theme.checkout_bg_color,
    '--color-primary': theme.checkout_accent_color,
    '--color-accent': theme.checkout_accent_color,
    '--color-header-bg': theme.checkout_header_bg_color,
    '--color-header-fg': theme.checkout_header_text_color,
    '--color-btn-bg': theme.checkout_step_button_color,
    '--color-btn-fg': theme.checkout_step_button_text_color,
    '--color-btn-hover': theme.checkout_step_button_color,
  };
  const css =
    `.checkout-scope{${Object.entries(vars)
      .map(([k, v]) => `${k}:${sanitize(v)}`)
      .join(';')}}` +
    // Borda um pouco mais escura em todos os campos do checkout (menos os que
    // estão em erro, que já ficam vermelhos). Sutil — não é preto.
    `.checkout-scope input:not([type=radio]):not([type=checkbox]):not([aria-invalid=true]),` +
    `.checkout-scope select:not([aria-invalid=true]),` +
    `.checkout-scope textarea:not([aria-invalid=true]){border-color:rgba(17,24,39,.28)}` +
    `.checkout-scope input:not([type=radio]):not([type=checkbox]):not([aria-invalid=true]):focus-visible,` +
    `.checkout-scope select:not([aria-invalid=true]):focus-visible,` +
    `.checkout-scope textarea:not([aria-invalid=true]):focus-visible{border-color:rgba(17,24,39,.55)}`;
  return <style id="ecom-checkout-theme" dangerouslySetInnerHTML={{ __html: css }} />;
}
