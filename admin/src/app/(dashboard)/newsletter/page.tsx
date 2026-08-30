'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { ColorField } from '@/components/color-field';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';


type ColorKey =
  | 'newsletter_bg_color'
  | 'newsletter_text_color'
  | 'newsletter_button_color'
  | 'newsletter_button_text_color'
  | 'lead_popup_bg_color'
  | 'lead_popup_text_color'
  | 'lead_popup_button_color'
  | 'lead_popup_button_text_color';

const COLORS: { key: ColorKey; label: string }[] = [
  { key: 'newsletter_bg_color', label: 'Fundo do bloco' },
  { key: 'newsletter_text_color', label: 'Texto do bloco' },
  { key: 'newsletter_button_color', label: 'Fundo do botão' },
  { key: 'newsletter_button_text_color', label: 'Texto do botão' },
];

const POPUP_COLORS: { key: ColorKey; label: string }[] = [
  { key: 'lead_popup_bg_color', label: 'Fundo do popup' },
  { key: 'lead_popup_text_color', label: 'Texto do popup' },
  { key: 'lead_popup_button_color', label: 'Fundo do botão' },
  { key: 'lead_popup_button_text_color', label: 'Texto do botão' },
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
      lead_popup_enabled: theme.lead_popup_enabled,
      lead_capture_enabled: theme.lead_capture_enabled,
      lead_popup_title: theme.lead_popup_title,
      lead_popup_subtitle: theme.lead_popup_subtitle,
      lead_popup_coupon_code: theme.lead_popup_coupon_code,
      lead_popup_bg_color: theme.lead_popup_bg_color,
      lead_popup_text_color: theme.lead_popup_text_color,
      lead_popup_button_color: theme.lead_popup_button_color,
      lead_popup_button_text_color: theme.lead_popup_button_text_color,
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
              <h2 className="text-lg font-semibold">Cores do bloco de newsletter</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {COLORS.map((f) => (
                  <ColorField
                    key={f.key}
                    label={f.label}
                    value={String(theme[f.key] ?? '#000000')}
                    onChange={(hex) => set(f.key, hex as never)}
                  />
                ))}
              </div>
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Popup de captura de leads</h2>
              <p className="text-xs text-text-muted">
                Aberto pelo link “Cadastre-se e ganhe…” na página do produto. Se um cupom for
                informado, ele é mostrado e enviado por e-mail ao lead.
              </p>
              <Checkbox
                label="Ativar a captura de leads (formulário da home)"
                checked={theme.lead_capture_enabled}
                onChange={(v) => set('lead_capture_enabled', v)}
              />
              <Checkbox
                label="Ativar o popup de captura na página do produto"
                checked={theme.lead_popup_enabled}
                onChange={(v) => set('lead_popup_enabled', v)}
              />
              <Input
                label="Título do popup"
                value={theme.lead_popup_title}
                onChange={(e) => set('lead_popup_title', e.target.value)}
              />
              <Input
                label="Subtítulo do popup"
                value={theme.lead_popup_subtitle}
                onChange={(e) => set('lead_popup_subtitle', e.target.value)}
              />
              <Input
                label="Cupom enviado ao lead (opcional)"
                placeholder="Ex.: BEMVINDO10"
                value={theme.lead_popup_coupon_code ?? ''}
                onChange={(e) => set('lead_popup_coupon_code', e.target.value || null)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                {POPUP_COLORS.map((f) => (
                  <ColorField
                    key={f.key}
                    label={f.label}
                    value={String(theme[f.key] ?? '#000000')}
                    onChange={(hex) => set(f.key, hex as never)}
                  />
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
