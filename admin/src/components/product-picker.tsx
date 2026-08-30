'use client';

import { useEffect, useRef, useState } from 'react';
import { Input } from '@ecom/ui';
import { productsApi } from '@/modules/catalog/api';

export interface PickerResult {
  id: string;
  name: string;
  slug: string;
  primary_image_url?: string | null;
}

/** Campo de busca de produtos com dropdown de resultados. Chama onPick ao escolher. */
export function ProductPicker({
  excludeIds = [],
  label = 'Buscar produto para adicionar',
  onPick,
}: {
  excludeIds?: string[];
  label?: string;
  onPick: (p: PickerResult) => void;
}) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<PickerResult[]>([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      setLoading(true);
      const res = await productsApi.list({ q: q.trim(), page: 1, page_size: 20 });
      setLoading(false);
      if (res.ok) {
        setResults(
          res.data.items.map((p) => ({
            id: p.id,
            name: p.name,
            slug: p.slug,
            primary_image_url: p.primary_image_url,
          })),
        );
        setOpen(true);
      }
    }, 300);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [q]);

  const visible = results.filter((r) => !excludeIds.includes(r.id));

  return (
    <div className="relative max-w-md">
      <Input
        label={label}
        placeholder="Digite ao menos 2 letras"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      {open && q.trim().length >= 2 && (
        <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-card border border-surface-border bg-surface shadow-lg">
          {loading && <li className="px-3 py-2 text-sm text-text-muted">Buscando…</li>}
          {!loading && visible.length === 0 && (
            <li className="px-3 py-2 text-sm text-text-muted">Nenhum produto.</li>
          )}
          {visible.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-bg-subtle"
                onClick={() => {
                  onPick(r);
                  setQ('');
                  setOpen(false);
                }}
              >
                <span className="h-8 w-8 shrink-0 overflow-hidden rounded bg-bg-subtle">
                  {r.primary_image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={r.primary_image_url} alt="" className="h-full w-full object-cover" />
                  )}
                </span>
                {r.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
