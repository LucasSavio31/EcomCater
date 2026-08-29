'use client';

import { useId } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type { ProductSort } from '@/modules/catalog/types';

const OPTIONS: { value: ProductSort; label: string }[] = [
  { value: 'relevancia', label: 'Relevância' },
  { value: 'menor-preco', label: 'Menor preço' },
  { value: 'maior-preco', label: 'Maior preço' },
  { value: 'lancamentos', label: 'Lançamentos' },
];

export function PlpSort({ total }: { total: number }) {
  const id = useId();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const current = (params.get('sort') as ProductSort | null) ?? 'relevancia';

  function onChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const next = new URLSearchParams(params.toString());
    if (event.target.value === 'relevancia') next.delete('sort');
    else next.set('sort', event.target.value);
    next.delete('page');
    router.push(`${pathname}?${next.toString()}`);
  }

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-text-muted" aria-live="polite">
        {total} {total === 1 ? 'produto' : 'produtos'}
      </p>
      <label className="flex items-center gap-2 text-sm">
        <span className="hidden sm:inline" id={id}>
          Ordenar por
        </span>
        <select
          aria-labelledby={id}
          value={current}
          onChange={onChange}
          className="min-h-touch rounded-card border border-surface-border bg-surface px-2 text-sm text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
