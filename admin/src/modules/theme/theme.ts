import 'server-only';

/** Subconjunto de `GET /api/theme` que o admin usa para aplicar o mesmo visual da loja. */
export interface AdminTheme {
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  text_color: string;
  bg_color: string;
  font_family: string;
}

export const NEUTRAL_ADMIN_THEME: AdminTheme = {
  primary_color: '#111111',
  secondary_color: '#4B5563',
  accent_color: '#DC2626',
  text_color: '#111827',
  bg_color: '#FFFFFF',
  font_family: 'Inter, system-ui, sans-serif',
};

const API_URL =
  process.env.NEXT_PUBLIC_ADMIN_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  'http://localhost:8000';

/** Nunca lança: fora do ar (build/incidente) → paleta neutra. */
export async function getAdminTheme(): Promise<AdminTheme> {
  try {
    const res = await fetch(`${API_URL}/api/theme`, {
      next: { tags: ['theme'], revalidate: 300 },
    });
    if (!res.ok) return NEUTRAL_ADMIN_THEME;
    const data = (await res.json()) as Partial<AdminTheme>;
    return { ...NEUTRAL_ADMIN_THEME, ...data };
  } catch {
    return NEUTRAL_ADMIN_THEME;
  }
}

export function themeToCssVars(theme: AdminTheme): string {
  const vars: Record<string, string> = {
    '--color-primary': theme.primary_color,
    '--color-secondary': theme.secondary_color,
    '--color-text': theme.text_color,
    '--color-bg': theme.bg_color,
    '--color-surface': theme.bg_color,
    '--font-family': theme.font_family,
    // Destaque e botões do painel são SEMPRE pretos com texto branco — não
    // seguem a cor de destaque/botão que o lojista configura para a loja.
    '--color-accent': '#111111',
    '--color-accent-fg': '#FFFFFF',
    '--color-btn-bg': '#111111',
    '--color-btn-fg': '#FFFFFF',
    '--color-btn-hover': '#000000',
  };
  const body = Object.entries(vars)
    .map(([k, v]) => `${k}:${String(v).replace(/[<>]/g, '')};`)
    .join('');
  return `:root{${body}}`;
}
