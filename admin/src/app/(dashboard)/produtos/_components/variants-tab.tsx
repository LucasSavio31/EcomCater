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
      {/* Editor de eixos */}
      <Card variant="outline" className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Eixos de variação</h3>
          {!hasVariants && (
            <Button size="sm" variant="outline" onClick={() => setDraft((d) => [...d, { key: nextKey(), name: '', is_size: false, values: [] }])}>
              Adicionar eixo
            </Button>
          )}
        </div>

        {hasVariants && (
          <p className="rounded-card bg-bg-subtle p-3 text-xs text-text-muted">
            Os eixos ficam travados porque já existem variações. Exclua todas as variações abaixo para editá-los.
          </p>
        )}

        {draft.length === 0 && <p className="text-sm text-text-muted">Nenhum eixo. Produto simples (sem variações).</p>}

        {draft.map((t) => (
          <div key={t.key} className="flex flex-col gap-3 rounded-card border border-surface-border p-3">
            <div className="flex flex-wrap items-end gap-3">
              <Input
                label="Nome do eixo"
                placeholder="Ex.: Cor, Numeração"
                value={t.name}
                disabled={hasVariants}
                onChange={(e) =>
                  setDraft((d) => d.map((x) => (x.key === t.key ? { ...x, name: e.target.value } : x)))
                }
              />
              <Checkbox
                label="É o eixo de tamanho"
                checked={t.is_size}
                disabled={hasVariants}
                onChange={(v) => setDraft((d) => d.map((x) => (x.key === t.key ? { ...x, is_size: v } : x)))}
              />
              {!hasVariants && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setDraft((d) => d.filter((x) => x.key !== t.key))}
                >
                  Remover eixo
                </Button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {t.values.map((v) => (
                <span key={v.key} className="flex items-center gap-1 rounded-card border border-surface-border px-2 py-1 text-sm">
                  <input
                    className="w-24 bg-transparent focus:outline-none"
                    value={v.value}
                    disabled={hasVariants}
                    onChange={(e) =>
                      setDraft((d) =>
                        d.map((x) =>
                          x.key === t.key
                            ? { ...x, values: x.values.map((y) => (y.key === v.key ? { ...y, value: e.target.value } : y)) }
                            : x,
                        ),
                      )
                    }
                  />
                  {!hasVariants && (
                    <button
                      type="button"
                      aria-label="Remover valor"
                      className="text-text-muted hover:text-danger"
                      onClick={() =>
                        setDraft((d) =>
                          d.map((x) => (x.key === t.key ? { ...x, values: x.values.filter((y) => y.key !== v.key) } : x)),
                        )
                      }
                    >
                      ×
                    </button>
                  )}
                </span>
              ))}
              {!hasVariants && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setDraft((d) =>
                      d.map((x) => (x.key === t.key ? { ...x, values: [...x.values, { key: nextKey(), value: '' }] } : x)),
                    )
                  }
                >
                  + valor
                </Button>
              )}
            </div>
          </div>
        ))}

        {!hasVariants && (
          <Button loading={savingAxes} onClick={() => void saveAxes()} className="self-start">
            Salvar eixos
          </Button>
        )}
      </Card>

      <VariantMatrix product={product} onChanged={onChanged} />
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
        Defina ao menos um eixo para gerar a matriz de variações. Sem eixos, o estoque é controlado no próprio produto.
      </Card>
    );
  }

  return (
    <Card variant="outline" className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold">Matriz de variações</h3>
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
  const [stock, setStock] = useState(String(variant?.stock_qty ?? 0));
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
      stock_qty: Number(stock) || 0,
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
        <Input label="Estoque" inputMode="numeric" value={stock} onChange={(e) => setStock(e.target.value)} />
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
