'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

type ColorKey =
  | 'newsletter_bg_color'
  | 'newsletter_text_color'
  | 'newsletter_button_color'
  | 'newsletter_button_text_color';

const COLORS: { key: ColorKey; label: string }[] = [
  { key: 'newsletter_bg_color', label: 'Fundo do bloco' },
  { key: 'newsletter_text_color', label: 'Texto do bloco' },
  { key: 'newsletter_button_color', label: 'Fundo do botão' },
  { key: 'newsletter_button_text_color', label: 'Texto do botão' },
];

export default function NewsletterPage() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [saving, setSaving] = useState(false);

  const theme = draft ?? data;
  const dirty = draft !== null;
  const set = <K extends keyof Theme>(k: K, v: Theme[K]) => {
    if (!theme) return;
    setDraft({ ...theme, [k]: v });
  };

  async function save() {
    if (!theme) return;
    setSaving(true);
    const res = await appearanceApi.putTheme({
      newsletter_enabled: theme.newsletter_enabled,
      newsletter_title: theme.newsletter_title,
      newsletter_subtitle: theme.newsletter_subtitle,
      newsletter_bg_color: theme.newsletter_bg_color,
      newsletter_text_color: theme.newsletter_text_color,
      newsletter_button_color: theme.newsletter_button_color,
      newsletter_button_text_color: theme.newsletter_button_text_color,
    });
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Newsletter salva e aplicada na loja.');
  }

  function ColorRow({ f }: { f: { key: ColorKey; label: string } }) {
    if (!theme) return null;
    const raw = String(theme[f.key] ?? '#000000');
    const valid = HEX_RE.test(raw);
    return (
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">{f.label}</label>
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={valid ? raw.slice(0, 7) : '#000000'}
            onChange={(e) => set(f.key, e.target.value)}
            className="h-10 w-14 shrink-0 rounded-card border border-surface-border"
            aria-label={f.label}
          />
          <Input value={raw} aria-invalid={!valid} onChange={(e) => set(f.key, e.target.value)} className="flex-1" />
        </div>
        {!valid && <span className="text-xs text-red-600">Use #RRGGBB.</span>}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Newsletter"
        description="Bloco de captura de e-mail na home. Os inscritos ficam na lista para campanhas."
      />
      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {theme && (
          <div className="flex max-w-2xl flex-col gap-5">
            <Card variant="outline" className="flex flex-col gap-4">
              <Checkbox
                label="Exibir o bloco de newsletter na home"
                checked={theme.newsletter_enabled}
                onChange={(v) => set('newsletter_enabled', v)}
              />
              <Input
                label="Título"
                value={theme.newsletter_title}
                onChange={(e) => set('newsletter_title', e.target.value)}
              />
              <Input
                label="Subtítulo"
                value={theme.newsletter_subtitle}
                onChange={(e) => set('newsletter_subtitle', e.target.value)}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Cores</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {COLORS.map((f) => (
                  <ColorRow key={f.key} f={f} />
                ))}
              </div>
            </Card>

            <div className="flex items-center gap-3">
              <Button loading={saving} onClick={() => void save()}>
                Salvar
              </Button>
              {dirty && (
                <button
                  type="button"
                  className="text-sm text-text-muted underline"
                  onClick={() => setDraft(null)}
                >
                  Descartar
                </button>
              )}
            </div>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
