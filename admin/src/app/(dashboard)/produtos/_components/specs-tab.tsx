'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { useToast } from '@/components/toast';
import { productsApi } from '@/modules/catalog/api';
import type { ProductDetail, ProductSpec } from '@/modules/catalog/types';

interface Props {
  product: ProductDetail;
  onChanged: (p: ProductDetail) => void;
}

interface Row extends ProductSpec {
  key: string;
}

let seq = 0;
const key = (): string => {
  seq += 1;
  return `s${seq}`;
};

export function SpecsTab({ product, onChanged }: Props) {
  const toast = useToast();
  const [rows, setRows] = useState<Row[]>(() =>
    product.specs.map((s) => ({ ...s, key: key() })),
  );
  const [saving, setSaving] = useState(false);

  function update(k: string, patch: Partial<Row>): void {
    setRows((prev) => prev.map((r) => (r.key === k ? { ...r, ...patch } : r)));
  }

  async function save(): Promise<void> {
    const payload: ProductSpec[] = rows
      .filter((r) => r.label.trim() && r.value.trim())
      .map((r, i) => ({
        group: r.group?.trim() || null,
        label: r.label.trim(),
        value: r.value.trim(),
        position: i,
      }));
    setSaving(true);
    const result = await productsApi.putSpecs(product.id, payload);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Especificações salvas.');
    const fresh = await productsApi.get(product.id);
    if (fresh.ok) onChanged(fresh.data);
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Especificações (chave/valor)</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setRows((r) => [...r, { key: key(), group: '', label: '', value: '' }])}
        >
          Adicionar linha
        </Button>
      </div>

      {rows.length === 0 && <p className="text-sm text-text-muted">Nenhuma especificação.</p>}

      {rows.map((r) => (
        <div key={r.key} className="grid gap-2 rounded-card border border-surface-border p-3 sm:grid-cols-[1fr_1fr_2fr_auto]">
          <Input
            label="Grupo"
            placeholder="Ex.: Materiais"
            value={r.group ?? ''}
            onChange={(e) => update(r.key, { group: e.target.value })}
          />
          <Input label="Rótulo" value={r.label} onChange={(e) => update(r.key, { label: e.target.value })} />
          <Input label="Valor" value={r.value} onChange={(e) => update(r.key, { value: e.target.value })} />
          <div className="flex items-end">
            <Button size="sm" variant="ghost" onClick={() => setRows((prev) => prev.filter((x) => x.key !== r.key))}>
              Remover
            </Button>
          </div>
        </div>
      ))}

      <Button loading={saving} onClick={() => void save()} className="self-start">
        Salvar especificações
      </Button>
    </Card>
  );
}
