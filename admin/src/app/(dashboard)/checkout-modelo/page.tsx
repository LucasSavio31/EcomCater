'use client';

import { useEffect, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { ColorField } from '@/components/color-field';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { ProductPicker } from '@/components/product-picker';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type Theme } from '@/modules/appearance/api';
import { productsApi } from '@/modules/catalog/api';
import { revalidateStore } from '@/lib/revalidate-store';


type ColorKey =
  | 'checkout_bg_color'
  | 'checkout_header_bg_color'
  | 'checkout_header_text_color'
  | 'checkout_step_button_color'
  | 'checkout_step_button_text_color'
  | 'checkout_button_color'
  | 'checkout_button_text_color'
  | 'checkout_step_active_bg_color'
  | 'checkout_step_active_text_color'
  | 'checkout_accent_color';

const COLOR_FIELDS: { key: ColorKey; label: string }[] = [
  { key: 'checkout_bg_color', label: 'Fundo da página' },
  { key: 'checkout_header_bg_color', label: 'Fundo do cabeçalho' },
  { key: 'checkout_header_text_color', label: 'Texto do cabeçalho' },
  { key: 'checkout_step_button_color', label: 'Fundo dos botões de etapa (Continuar/Calcular)' },
  { key: 'checkout_step_button_text_color', label: 'Texto dos botões de etapa' },
  { key: 'checkout_button_color', label: 'Fundo do botão finalizar' },
  { key: 'checkout_button_text_color', label: 'Texto do botão finalizar' },
  { key: 'checkout_step_active_bg_color', label: 'Fundo da etapa ativa (1,2,3,4)' },
  { key: 'checkout_step_active_text_color', label: 'Texto da etapa ativa' },
  { key: 'checkout_accent_color', label: 'Destaque (seleção, links)' },
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

  const [products, setProducts] = useState<{ slug: string; name: string }[]>([]);
  useEffect(() => {
    void productsApi.list({ page: 1, page_size: 200 }).then((r) => {
      if (r.ok) setProducts(r.data.items.map((p) => ({ slug: p.slug, name: p.name })));
    });
  }, []);

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
      checkout_animated_card: theme.checkout_animated_card,
      checkout_show_review: theme.checkout_show_review,
      checkout_review_position: theme.checkout_review_position,
      checkout_orderbump_enabled: theme.checkout_orderbump_enabled,
      checkout_orderbump_product_id: theme.checkout_orderbump_product_id ?? '',
      checkout_orderbump_product_ids: theme.checkout_orderbump_product_ids ?? [],
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
              <Checkbox
                label="Cartão de crédito animado"
                hint="Mostra um cartão que atualiza e vira ao focar o CVV."
                checked={theme.checkout_animated_card}
                onChange={(v) => set('checkout_animated_card', v)}
              />
              <Checkbox
                label="Exibir a revisão do pedido"
                checked={theme.checkout_show_review}
                onChange={(v) => set('checkout_show_review', v)}
              />
              <Select
                label="Posição da revisão"
                value={theme.checkout_review_position}
                options={[
                  { value: 'side', label: 'Lado direito da tela' },
                  { value: 'top', label: 'Topo, em dropdown' },
                ]}
                onChange={(e) =>
                  set('checkout_review_position', e.target.value as Theme['checkout_review_position'])
                }
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
              <h2 className="text-lg font-semibold">Order bump</h2>
              <Checkbox
                label="Oferecer um produto extra no checkout"
                hint="Aparece um convite para o cliente adicionar outro produto ao pedido."
                checked={theme.checkout_orderbump_enabled}
                onChange={(v) => set('checkout_orderbump_enabled', v)}
              />
              {theme.checkout_orderbump_enabled && (
                <div className="flex flex-col gap-2">
                  <span className="text-sm font-medium">Produtos oferecidos</span>
                  {(theme.checkout_orderbump_product_ids ?? []).length === 0 ? (
                    <p className="text-sm text-text-muted">Nenhum produto selecionado.</p>
                  ) : (
                    <ul className="flex flex-wrap gap-2">
                      {(theme.checkout_orderbump_product_ids ?? []).map((slug) => (
                        <li
                          key={slug}
                          className="flex items-center gap-2 rounded-card border border-surface-border px-2 py-1 text-sm"
                        >
                          {products.find((p) => p.slug === slug)?.name ?? slug}
                          <button
                            type="button"
                            aria-label="Remover"
                            className="text-text-muted hover:text-danger"
                            onClick={() =>
                              set(
                                'checkout_orderbump_product_ids',
                                (theme.checkout_orderbump_product_ids ?? []).filter((s) => s !== slug),
                              )
                            }
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <ProductPicker
                    label="Buscar produto para oferecer"
                    onPick={(p) => {
                      const cur = theme.checkout_orderbump_product_ids ?? [];
                      if (!cur.includes(p.slug)) {
                        set('checkout_orderbump_product_ids', [...cur, p.slug]);
                      }
                    }}
                  />
                </div>
              )}
            </Card>

            <Card variant="outline" className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold">Cores do checkout</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {COLOR_FIELDS.map((f) => (
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
