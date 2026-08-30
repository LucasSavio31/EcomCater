'use client';

import { useMemo, useState } from 'react';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { Checkbox } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { centsToInput, inputToCents } from '@/lib/format';
import { productsApi } from '@/modules/catalog/api';
import type { OptionType, ProductDetail, Variant } from '@/modules/catalog/types';

interface Props {
  product: ProductDetail;
  onChanged: (p: ProductDetail) => void;
}

interface DraftValue {
  key: string;
  value: string;
}
interface DraftType {
  key: string;
  name: string;
  is_size: boolean;
  is_color: boolean;
  values: DraftValue[];
}

let counter = 0;
const nextKey = (): string => {
  counter += 1;
  return `k${counter}`;
};

function toDraft(types: OptionType[]): DraftType[] {
  return types.map((t) => ({
    key: nextKey(),
    name: t.name,
    is_size: t.is_size,
    is_color: !!t.is_color,
    values: t.values.map((v) => ({ key: v.id ?? nextKey(), value: v.value })),
  }));
}

export function VariantsTab({ product, onChanged }: Props) {
  const toast = useToast();
  const hasVariants = product.variants.length > 0;
  const [draft, setDraft] = useState<DraftType[]>(() => toDraft(product.option_types));
  const [savingAxes, setSavingAxes] = useState(false);

  async function refresh(): Promise<void> {
    const result = await productsApi.get(product.id);
    if (result.ok) onChanged(result.data);
  }

  async function saveAxes(): Promise<void> {
    const payload: OptionType[] = draft
      .filter((t) => t.name.trim() && t.values.some((v) => v.value.trim()))
      .map((t, i) => ({
        name: t.name.trim(),
        is_size: t.is_size,
        is_color: t.is_color,
        position: i,
        values: t.values
          .filter((v) => v.value.trim())
          .map((v, j) => ({ value: v.value.trim(), position: j })),
      }));
    setSavingAxes(true);
    const result = await productsApi.putOptionTypes(product.id, payload);
    setSavingAxes(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Eixos salvos.');
    await refresh();
  }

  return (
    <div className="flex flex-col gap-6">
      <Card variant="outline" className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Tipos de variação</h3>
          {!hasVariants && (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setDraft((d) => [
                  ...d,
                  { key: nextKey(), name: '', is_size: false, is_color: false, values: [] },
                ])
              }
            >
              Adicionar tipo
            </Button>
          )}
        </div>

        {hasVariants ? (
          <>
            <p className="rounded-card bg-bg-subtle p-3 text-xs text-text-muted">
              Já existem variações cadastradas. Você ainda pode <b>incluir/excluir valores</b> e marcar
              qual tipo é <b>Cor</b>. Para renomear ou remover um tipo inteiro, exclua as variações abaixo.
            </p>
            {product.option_types.map((t) => (
              <LiveAxis key={t.id} product={product} type={t} onChanged={onChanged} />
            ))}
          </>
        ) : (
          <>
            {draft.length === 0 && (
              <p className="text-sm text-text-muted">Nenhum tipo. Produto simples (sem variações).</p>
            )}
            {draft.map((t) => (
              <div
                key={t.key}
                className="flex flex-col gap-3 rounded-card border border-surface-border p-3"
              >
                <div className="flex flex-wrap items-end gap-3">
                  <Input
                    label="Nome do tipo"
                    placeholder="Ex.: Numeração, Cor"
                    value={t.name}
                    onChange={(e) =>
                      setDraft((d) =>
                        d.map((x) => (x.key === t.key ? { ...x, name: e.target.value } : x)),
                      )
                    }
                  />
                  <Checkbox
                    label="É o tipo de numeração/tamanho"
                    checked={t.is_size}
                    onChange={(v) =>
                      setDraft((d) => d.map((x) => (x.key === t.key ? { ...x, is_size: v } : x)))
                    }
                  />
                  <Checkbox
                    label="É o tipo de cor (mostra miniaturas)"
                    checked={t.is_color}
                    onChange={(v) =>
                      setDraft((d) => d.map((x) => (x.key === t.key ? { ...x, is_color: v } : x)))
                    }
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setDraft((d) => d.filter((x) => x.key !== t.key))}
                  >
                    Remover tipo
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {t.values.map((v) => (
                    <span
                      key={v.key}
                      className="flex items-center gap-1 rounded-card border border-surface-border px-2 py-1 text-sm"
                    >
                      <input
                        className="w-24 bg-transparent focus:outline-none"
                        value={v.value}
                        onChange={(e) =>
                          setDraft((d) =>
                            d.map((x) =>
                              x.key === t.key
                                ? {
                                    ...x,
                                    values: x.values.map((y) =>
                                      y.key === v.key ? { ...y, value: e.target.value } : y,
                                    ),
                                  }
                                : x,
                            ),
                          )
                        }
                      />
                      <button
                        type="button"
                        aria-label="Remover valor"
                        className="text-text-muted hover:text-danger"
                        onClick={() =>
                          setDraft((d) =>
                            d.map((x) =>
                              x.key === t.key
                                ? { ...x, values: x.values.filter((y) => y.key !== v.key) }
                                : x,
                            ),
                          )
                        }
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      setDraft((d) =>
                        d.map((x) =>
                          x.key === t.key
                            ? { ...x, values: [...x.values, { key: nextKey(), value: '' }] }
                            : x,
                        ),
                      )
                    }
                  >
                    + valor
                  </Button>
                </div>
              </div>
            ))}
            <Button loading={savingAxes} onClick={() => void saveAxes()} className="self-start">
              Salvar tipos
            </Button>
          </>
        )}
      </Card>

      <VariantMatrix product={product} onChanged={onChanged} />
    </div>
  );
}

/* ----------------------- Edição "ao vivo" quando já há variações ----------------------- */

function LiveAxis({
  product,
  type,
  onChanged,
}: {
  product: ProductDetail;
  type: OptionType;
  onChanged: (p: ProductDetail) => void;
}) {
  const toast = useToast();
  const [newValue, setNewValue] = useState('');
  const [busy, setBusy] = useState(false);

  const usedValueIds = useMemo(
    () => new Set(product.variants.flatMap((v) => v.option_value_ids)),
    [product.variants],
  );

  async function apply<T>(p: Promise<{ ok: true; data: T } | { ok: false; error: { message: string } }>) {
    setBusy(true);
    const r = await p;
    setBusy(false);
    if (!r.ok) {
      toast.error(r.error.message);
      return;
    }
    onChanged(r.data as unknown as ProductDetail);
  }

  return (
    <div className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-sm font-semibold">{type.name}</span>
        {type.is_size && <Badge tone="neutral">numeração</Badge>}
        <Checkbox
          label="É o tipo de cor (miniaturas na loja)"
          checked={!!type.is_color}
          disabled={busy}
          onChange={(v) =>
            void apply(productsApi.patchOptionType(product.id, type.id!, { is_color: v }))
          }
        />
      </div>

      <div className="flex flex-col gap-2">
        {type.values.map((val) => {
          const inUse = val.id ? usedValueIds.has(val.id) : false;
          return (
            <div
              key={val.id}
              className="flex flex-wrap items-center gap-2 rounded-card bg-bg-subtle px-2 py-1.5"
            >
              <span className="min-w-[3rem] text-sm font-medium">{val.value}</span>

              {type.is_color && (
                <label className="flex items-center gap-2 text-xs text-text-muted">
                  Miniatura:
                  <select
                    className="min-h-touch rounded-card border border-surface-border bg-surface px-2 text-sm text-text"
                    value={val.image_id ?? ''}
                    disabled={busy}
                    onChange={(e) =>
                      void apply(
                        productsApi.updateOptionValue(product.id, val.id!, {
                          image_id: e.target.value || null,
                        }),
                      )
                    }
                  >
                    <option value="">— nenhuma —</option>
                    {product.images.map((img, i) => (
                      <option key={img.id} value={img.id}>
                        {img.alt || `Imagem ${i + 1}`}
                        {img.is_primary ? ' (principal)' : ''}
                      </option>
                    ))}
                  </select>
                  {val.swatch_thumb_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={val.swatch_thumb_url}
                      alt=""
                      className="h-8 w-12 rounded border border-surface-border object-cover"
                    />
                  )}
                </label>
              )}

              <button
                type="button"
                disabled={busy || inUse}
                title={inUse ? 'Valor em uso por uma variação' : 'Excluir valor'}
                onClick={() => void apply(productsApi.deleteOptionValue(product.id, val.id!))}
                className="ml-auto rounded p-1 text-xs text-danger hover:bg-surface-border disabled:opacity-40"
              >
                excluir
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex items-end gap-2">
        <Input
          label="Incluir valor"
          placeholder={type.is_color ? 'Ex.: Café' : 'Ex.: 46'}
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
        />
        <Button
          size="sm"
          disabled={busy || !newValue.trim()}
          onClick={async () => {
            await apply(productsApi.addOptionValue(product.id, type.id!, newValue.trim()));
            setNewValue('');
          }}
        >
          Incluir
        </Button>
      </div>
    </div>
  );
}

interface Combo {
  ids: string[];
  labels: string[];
}

function VariantMatrix({ product, onChanged }: Props) {
  const toast = useToast();
  const { option_types: types, variants } = product;

  const combos: Combo[] = useMemo(() => {
    if (types.length === 0) return [];
    const axes = types.map((t) => t.values.map((v) => ({ id: v.id ?? '', label: v.value })));
    let acc: Combo[] = [{ ids: [], labels: [] }];
    for (const axis of axes) {
      const next: Combo[] = [];
      for (const partial of acc) {
        for (const val of axis) {
          next.push({ ids: [...partial.ids, val.id], labels: [...partial.labels, val.label] });
        }
      }
      acc = next;
    }
    return acc.filter((c) => c.ids.every(Boolean));
  }, [types]);

  function findVariant(ids: string[]): Variant | undefined {
    return variants.find(
      (v) => v.option_value_ids.length === ids.length && ids.every((id) => v.option_value_ids.includes(id)),
    );
  }

  async function refresh(): Promise<void> {
    const result = await productsApi.get(product.id);
    if (result.ok) onChanged(result.data);
  }

  if (types.length === 0) {
    return (
      <Card variant="outline" className="text-sm text-text-muted">
        Defina ao menos um tipo para gerar a matriz de variações. Sem tipos, o estoque é controlado no próprio produto.
      </Card>
    );
  }

  return (
    <Card variant="outline" className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold">Matriz de variações (estoque/preço por combinação)</h3>
      <div className="flex flex-col gap-3">
        {combos.map((combo) => {
          const existing = findVariant(combo.ids);
          return (
            <VariantRow
              key={combo.ids.join('|')}
              productId={product.id}
              combo={combo}
              variant={existing}
              position={combos.indexOf(combo)}
              onSaved={refresh}
              onError={(m) => toast.error(m)}
              onOk={(m) => toast.success(m)}
            />
          );
        })}
      </div>
    </Card>
  );
}

interface VariantRowProps {
  productId: string;
  combo: Combo;
  variant: Variant | undefined;
  position: number;
  onSaved: () => Promise<void>;
  onError: (m: string) => void;
  onOk: (m: string) => void;
}

function VariantRow({ productId, combo, variant, position, onSaved, onError, onOk }: VariantRowProps) {
  const [sku, setSku] = useState(variant?.sku ?? '');
  // vazio = estoque ilimitado
  const [stock, setStock] = useState(
    variant?.stock_qty === null || variant?.stock_qty === undefined
      ? ''
      : String(variant.stock_qty),
  );
  const [price, setPrice] = useState(centsToInput(variant?.price_cents ?? null));
  const [active, setActive] = useState(variant?.is_active ?? true);
  const [busy, setBusy] = useState(false);

  async function save(): Promise<void> {
    if (!sku.trim()) {
      onError('Informe o SKU da variação.');
      return;
    }
    setBusy(true);
    const body = {
      sku: sku.trim(),
      option_value_ids: combo.ids,
      price_cents: inputToCents(price),
      stock_qty: stock.trim() === '' ? null : Number(stock) || 0,
      is_active: active,
      position,
    };
    const result = variant
      ? await productsApi.updateVariant(productId, variant.id, body)
      : await productsApi.createVariant(productId, body);
    setBusy(false);
    if (!result.ok) {
      onError(result.error.message);
      return;
    }
    onOk('Variação salva.');
    await onSaved();
  }

  async function remove(): Promise<void> {
    if (!variant) return;
    setBusy(true);
    const result = await productsApi.deleteVariant(productId, variant.id);
    setBusy(false);
    if (!result.ok) {
      onError(result.error.message);
      return;
    }
    onOk('Variação removida.');
    await onSaved();
  }

  return (
    <div className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        {combo.labels.map((l) => (
          <Badge key={l} tone="neutral">
            {l}
          </Badge>
        ))}
        {variant ? <Badge tone="success">cadastrada</Badge> : <Badge tone="warning">não cadastrada</Badge>}
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        <Input label="SKU" value={sku} onChange={(e) => setSku(e.target.value)} />
        <Input
          label="Estoque"
          inputMode="numeric"
          placeholder="∞ ilimitado"
          hint="Vazio = estoque ilimitado"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
        />
        <Input
          label="Preço (R$)"
          inputMode="decimal"
          placeholder="herda do produto"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
        <div className="flex items-end">
          <Checkbox label="Ativa" checked={active} onChange={setActive} />
        </div>
      </div>
      <div className="flex gap-2">
        <Button size="sm" loading={busy} onClick={() => void save()}>
          {variant ? 'Salvar' : 'Criar variação'}
        </Button>
        {variant && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => void remove()}>
            Excluir
          </Button>
        )}
      </div>
    </div>
  );
}
