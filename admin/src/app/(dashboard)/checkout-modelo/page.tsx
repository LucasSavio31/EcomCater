'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { revalidateStore } from '@/lib/revalidate-store';

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

type ColorKey =
  | 'checkout_bg_color'
  | 'checkout_header_bg_color'
  | 'checkout_header_text_color'
  | 'checkout_button_color'
  | 'checkout_button_text_color'
  | 'checkout_accent_color'
  | 'checkout_footer_bg_color'
  | 'checkout_footer_text_color';

const COLOR_FIELDS: { key: ColorKey; label: string }[] = [
  { key: 'checkout_bg_color', label: 'Fundo da página' },
  { key: 'checkout_header_bg_color', label: 'Fundo do cabeçalho' },
  { key: 'checkout_header_text_color', label: 'Texto do cabeçalho' },
  { key: 'checkout_button_color', label: 'Fundo do botão finalizar' },
  { key: 'checkout_button_text_color', label: 'Texto do botão finalizar' },
  { key: 'checkout_accent_color', label: 'Destaque (etapa ativa, seleção)' },
  { key: 'checkout_footer_bg_color', label: 'Fundo do rodapé' },
  { key: 'checkout_footer_text_color', label: 'Texto do rodapé' },
];

export default function CheckoutModeloPage() {
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
    const body: Partial<Theme> = {
      checkout_email_first: theme.checkout_email_first,
      checkout_container_width_px: theme.checkout_container_width_px,
      checkout_items_layout: theme.checkout_items_layout,
      checkout_show_coupon: theme.checkout_show_coupon,
      checkout_allow_qty_change: theme.checkout_allow_qty_change,
      checkout_footer_note: theme.checkout_footer_note,
      ...Object.fromEntries(COLOR_FIELDS.map((f) => [f.key, theme[f.key]])),
    };
    const res = await appearanceApi.putTheme(body);
    setSaving(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    await revalidateStore('theme');
    setData(res.data);
    setDraft(null);
    toast.success('Modelo do checkout salvo e aplicado.');
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
        title="Checkout"
        description="Modelo e cores do checkout — separados do restante da loja."
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {theme && (
          <div className="flex max-w-2xl flex-col gap-5">
            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Fluxo</h2>
              <Checkbox
                label="Pedir só o e-mail primeiro"
                hint="O checkout pede apenas o e-mail na 1ª etapa; CPF, nome e telefone vêm depois."
                checked={theme.checkout_email_first}
                onChange={(v) => set('checkout_email_first', v)}
              />
              <Checkbox
                label="Exibir campo de cupom no resumo"
                checked={theme.checkout_show_coupon}
                onChange={(v) => set('checkout_show_coupon', v)}
              />
              <Checkbox
                label="Permitir alterar a quantidade no resumo"
                checked={theme.checkout_allow_qty_change}
                onChange={(v) => set('checkout_allow_qty_change', v)}
              />
              <Select
                label="Layout dos itens no resumo"
                value={theme.checkout_items_layout}
                options={[
                  { value: 'with_thumb', label: 'Com miniatura' },
                  { value: 'simple', label: 'Lista simples' },
                ]}
                onChange={(e) =>
                  set('checkout_items_layout', e.target.value as Theme['checkout_items_layout'])
                }
              />
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium" htmlFor="ckt-width">
                  Largura do container (px)
                </label>
                <input
                  id="ckt-width"
                  type="range"
                  min={900}
                  max={1600}
                  step={20}
                  value={theme.checkout_container_width_px}
                  onChange={(e) => set('checkout_container_width_px', Number(e.target.value))}
                />
                <Input
                  inputMode="numeric"
                  value={String(theme.checkout_container_width_px)}
                  onChange={(e) =>
                    set('checkout_container_width_px', Math.max(900, Math.min(1600, Number(e.target.value) || 900)))
                  }
                  className="w-28"
                />
              </div>
              <Input
                label="Texto abaixo dos selos no rodapé (opcional)"
                value={theme.checkout_footer_note ?? ''}
                onChange={(e) => set('checkout_footer_note', e.target.value || null)}
              />
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Cores do checkout</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {COLOR_FIELDS.map((f) => (
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
                  Descartar alterações
                </button>
              )}
            </div>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
