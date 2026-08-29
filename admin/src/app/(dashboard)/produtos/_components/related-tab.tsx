'use client';

import { useEffect, useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { useToast } from '@/components/toast';
import { productsApi } from '@/modules/catalog/api';
import type { ProductDetail, ProductListItem } from '@/modules/catalog/types';

interface Props {
  product: ProductDetail;
  onChanged: (p: ProductDetail) => void;
}

export function RelatedTab({ product, onChanged }: Props) {
  const toast = useToast();
  const [ids, setIds] = useState<string[]>(product.related_product_ids ?? []);
  const [labels, setLabels] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const rp of product.related_products ?? []) map[rp.id] = rp.name;
    return map;
  });
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ProductListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setResults([]);
      return;
    }
    let active = true;
    setSearching(true);
    const t = window.setTimeout(async () => {
      const res = await productsApi.list({ q: term, page_size: 8 });
      if (!active) return;
      if (res.ok) setResults(res.data.items.filter((p) => p.id !== product.id));
      setSearching(false);
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(t);
    };
  }, [query, product.id]);

  function add(p: ProductListItem): void {
    if (ids.includes(p.id)) return;
    setIds((prev) => [...prev, p.id]);
    setLabels((prev) => ({ ...prev, [p.id]: p.name }));
    setQuery('');
    setResults([]);
  }

  async function save(): Promise<void> {
    setSaving(true);
    const result = await productsApi.update(product.id, { related_product_ids: ids });
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Relacionados salvos.');
    onChanged(result.data);
  }

  return (
    <Card variant="outline" className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold">Produtos relacionados</h3>

      <div className="relative">
        <Input
          label="Buscar produto"
          placeholder="Digite ao menos 2 letras"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {(results.length > 0 || searching) && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-card border border-surface-border bg-surface shadow-lg">
            {searching && <li className="px-3 py-2 text-sm text-text-muted">Buscando…</li>}
            {results.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-bg-subtle"
                  onClick={() => add(p)}
                >
                  {p.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ul className="flex flex-col gap-2">
        {ids.length === 0 && <li className="text-sm text-text-muted">Nenhum relacionado.</li>}
        {ids.map((id) => (
          <li
            key={id}
            className="flex items-center justify-between rounded-card border border-surface-border px-3 py-2 text-sm"
          >
            <span>{labels[id] ?? id}</span>
            <Button size="sm" variant="ghost" onClick={() => setIds((prev) => prev.filter((x) => x !== id))}>
              Remover
            </Button>
          </li>
        ))}
      </ul>

      <Button loading={saving} onClick={() => void save()} className="self-start">
        Salvar relacionados
      </Button>
    </Card>
  );
}
