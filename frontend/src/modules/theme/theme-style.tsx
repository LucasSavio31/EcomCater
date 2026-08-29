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
  return (
    <style
      id="ecom-theme"
      // CSS estático derivado do tema; sanitizado contra `<` / `>`.
      dangerouslySetInnerHTML={{ __html: serialize(themeToCssVars(theme)) }}
    />
  );
}
