'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { Checkbox } from '@/components/form-controls';
import { ImageUploader } from '@/components/image-uploader';
import { useToast } from '@/components/toast';
import { AsyncBoundary } from '@/components/async-boundary';
import { useResource } from '@/lib/use-resource';
import { centsToInput, inputToCents } from '@/lib/format';
import { appearanceApi, type Theme, type ThemeImageKind } from '@/modules/appearance/api';

const COLOR_FIELDS: Array<{ key: keyof Theme; label: string }> = [
  { key: 'primary_color', label: 'Primária' },
  { key: 'secondary_color', label: 'Secundária' },
  { key: 'accent_color', label: 'Destaque' },
  { key: 'text_color', label: 'Texto' },
  { key: 'bg_color', label: 'Fundo' },
];

export function ThemeTab() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getTheme());
  const [draft, setDraft] = useState<Theme | null>(null);
  const [saving, setSaving] = useState(false);

  const theme = draft ?? data;
  const set = <K extends keyof Theme>(k: K, v: Theme[K]): void => {
    if (!theme) return;
    setDraft({ ...theme, [k]: v });
  };

  async function save(): Promise<void> {
    if (!theme) return;
    setSaving(true);
    const result = await appearanceApi.putTheme(theme);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Tema salvo. A loja aplica após a revalidação.');
    setData(result.data);
    setDraft(null);
  }

  async function upload(kind: ThemeImageKind, file: File): Promise<void> {
    const result = await appearanceApi.uploadThemeImage(kind, file);
    if (!result.ok) throw new Error(result.error.message);
    setData(result.data);
    setDraft(null);
    toast.success('Imagem atualizada.');
  }

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {theme && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div className="flex flex-col gap-6">
            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Cores</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {COLOR_FIELDS.map((f) => (
                  <div key={f.key} className="flex flex-col gap-1">
                    <label className="text-sm font-medium" htmlFor={`color-${f.key}`}>
                      {f.label}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        id={`color-${f.key}`}
                        type="color"
                        value={String(theme[f.key] ?? '#000000')}
                        onChange={(e) => set(f.key, e.target.value as Theme[typeof f.key])}
                        className="h-10 w-14 rounded-card border border-surface-border"
                      />
                      <Input
                        value={String(theme[f.key] ?? '')}
                        onChange={(e) => set(f.key, e.target.value as Theme[typeof f.key])}
                        className="flex-1"
                      />
                    </div>
                  </div>
                ))}
              </div>
              <Input
                label="Família de fonte"
                value={theme.font_family}
                onChange={(e) => set('font_family', e.target.value)}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Barra superior e contato</h2>
              <Checkbox
                label="Exibir barra superior"
                checked={theme.top_bar_enabled}
                onChange={(v) => set('top_bar_enabled', v)}
              />
              <Input
                label="Mensagem da barra superior"
                value={theme.top_bar_message ?? ''}
                onChange={(e) => set('top_bar_message', e.target.value)}
              />
              <Input
                label="WhatsApp"
                value={theme.whatsapp_number ?? ''}
                onChange={(e) => set('whatsapp_number', e.target.value)}
              />
              <Input
                label="Frete grátis a partir de (R$)"
                inputMode="decimal"
                value={centsToInput(theme.free_shipping_threshold_cents)}
                onChange={(e) => set('free_shipping_threshold_cents', inputToCents(e.target.value))}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Logo e favicon</h2>
              <div className="flex flex-wrap gap-6">
                <ImageUploader
                  label="Logo"
                  aspect="wide"
                  currentUrl={theme.logo_url ?? null}
                  onSelect={(file) => upload('logo', file)}
                />
                <ImageUploader
                  label="Logo (mobile)"
                  aspect="square"
                  currentUrl={theme.logo_mobile_url ?? null}
                  onSelect={(file) => upload('logo_mobile', file)}
                />
                <ImageUploader
                  label="Favicon"
                  aspect="square"
                  currentUrl={theme.favicon_url ?? null}
                  onSelect={(file) => upload('favicon', file)}
                />
              </div>
            </Card>

            <Button loading={saving} onClick={() => void save()} className="self-start">
              Salvar tema
            </Button>
          </div>

          <Card variant="elevated" className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">Pré-visualização ao vivo</h2>
            <div
              className="flex flex-col gap-3 rounded-card border p-4"
              style={{
                background: theme.bg_color,
                color: theme.text_color,
                fontFamily: theme.font_family,
                borderColor: theme.secondary_color,
              }}
            >
              {theme.top_bar_enabled && theme.top_bar_message && (
                <div
                  className="rounded-card px-3 py-1 text-center text-xs"
                  style={{ background: theme.primary_color, color: theme.bg_color }}
                >
                  {theme.top_bar_message}
                </div>
              )}
              <div className="text-xl font-bold">Sua Loja</div>
              <p className="text-sm">Um parágrafo de exemplo mostrando a cor do texto.</p>
              <div className="flex gap-2">
                <span
                  className="rounded-card px-3 py-1.5 text-sm font-medium"
                  style={{ background: theme.primary_color, color: theme.bg_color }}
                >
                  Botão primário
                </span>
                <span
                  className="rounded-card px-3 py-1.5 text-sm font-medium"
                  style={{ background: theme.accent_color, color: '#fff' }}
                >
                  Destaque
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </AsyncBoundary>
  );
}
