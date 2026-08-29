import type { Metadata } from 'next';
import { Card } from '@ecom/ui';
import { getTheme } from '@/modules/theme';
import { buildMetadata } from '@/lib/seo';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = buildMetadata({
  description: 'Loja no ar — fundação da Fase 1.',
  path: '/',
});

export default async function HomePage() {
  const theme = await getTheme();

  const swatches: Array<{ label: string; value: string; varName: string }> = [
    { label: 'Primária', value: theme.primary_color, varName: '--color-primary' },
    { label: 'Secundária', value: theme.secondary_color, varName: '--color-secondary' },
    { label: 'Destaque', value: theme.accent_color, varName: '--color-accent' },
    { label: 'Texto', value: theme.text_color, varName: '--color-text' },
    { label: 'Fundo', value: theme.bg_color, varName: '--color-bg' },
  ];

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-2">
        <span className="inline-flex w-fit items-center rounded-card bg-accent px-3 py-1 text-sm font-medium text-accent-fg">
          Loja no ar
        </span>
        <h1 className="text-2xl font-bold sm:text-3xl">Fundação — Fase 1</h1>
        <p className="max-w-prose text-text-muted">
          Este é um placeholder. O tema abaixo vem de <code>GET /api/theme</code> e é
          injetado como CSS variables no SSR (sem rebuild). A vitrine real entra na Fase 3.
        </p>
      </section>

      <section aria-labelledby="tema-titulo" className="flex flex-col gap-3">
        <h2 id="tema-titulo" className="text-lg font-semibold">
          Tema aplicado (prova do SSR)
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {swatches.map((s) => (
            <Card key={s.varName} variant="outline" className="flex flex-col gap-2">
              <span
                className="h-16 w-full rounded-card border border-surface-border"
                style={{ backgroundColor: `var(${s.varName})` }}
                aria-hidden="true"
              />
              <span className="text-sm font-medium">{s.label}</span>
              <code className="text-xs text-text-muted">{s.value}</code>
            </Card>
          ))}
        </div>
        <p className="text-sm text-text-muted">
          Fonte: <span style={{ fontFamily: 'var(--font-family)' }}>{theme.font_family}</span>
        </p>
      </section>
    </div>
  );
}
