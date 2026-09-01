'use client';

import { useEffect, useRef, useState } from 'react';
import { Input } from '@ecom/ui';
import { productsApi } from '@/modules/catalog/api';
import { foldAccents } from '@/lib/format';

export interface PickerResult {
  id: string;
  name: string;
  slug: string;
  primary_image_url?: string | null;
}

/**
 * Combobox de produtos: abre um dropdown com a lista ao focar e filtra
 * conforme se digita (busca no servidor a partir de 2 letras).
 */
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
  const [base, setBase] = useState<PickerResult[]>([]); // lista inicial (sem busca)
  const [results, setResults] = useState<PickerResult[]>([]); // resultado da busca
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrap = useRef<HTMLDivElement | null>(null);

  // lista inicial ao montar
  useEffect(() => {
    void productsApi.list({ page: 1, page_size: 50 }).then((r) => {
      if (r.ok) {
        setBase(
          r.data.items.map((p) => ({
            id: p.id,
            name: p.name,
            slug: p.slug,
            primary_image_url: p.primary_image_url,
          })),
        );
      }
    });
  }, []);

  // busca no servidor com debounce
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      setLoading(true);
      const res = await productsApi.list({ q: q.trim(), page: 1, page_size: 30 });
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
      }
    }, 300);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [q]);

  // fecha ao clicar fora
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const source = q.trim().length >= 2 ? results : base;
  const needle = foldAccents(q);
  const visible = source
    .filter((r) => !excludeIds.includes(r.id))
    .filter((r) => (needle && q.trim().length < 2 ? foldAccents(r.name).includes(needle) : true));

  return (
    <div className="relative max-w-md" ref={wrap}>
      <Input
        label={label}
        placeholder="Clique para ver a lista ou digite para buscar"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      {open && (
        <ul className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-card border border-surface-border bg-surface shadow-lg">
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
