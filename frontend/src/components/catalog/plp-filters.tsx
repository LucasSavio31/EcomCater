'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Button, Drawer } from '@ecom/ui';
import type { ProductFacets } from '@/modules/catalog/types';
import { formatBRL } from '@/lib/format';

export interface FilterVisibility {
  size: boolean;
  price: boolean;
  category: boolean;
}

const ALL_VISIBLE: FilterVisibility = { size: true, price: true, category: true };

interface PlpFiltersProps {
  facets: ProductFacets;
  show?: FilterVisibility;
  /** Subcategorias (ou irmãs) navegáveis — o "filtro de categoria". */
  categoryLinks?: { name: string; path: string; active?: boolean }[];
}

function useFilterActions() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const push = (mutate: (next: URLSearchParams) => void) => {
    const next = new URLSearchParams(params.toString());
    mutate(next);
    next.delete('page');
    router.push(`${pathname}?${next.toString()}`);
  };

  return { params, push };
}

/** Formulário de filtros (categoria + preço + tamanho). Reflete e altera a URL. */
export function PlpFilters({ facets, show = ALL_VISIBLE, categoryLinks = [] }: PlpFiltersProps) {
  const { params, push } = useFilterActions();
  const selectedSizes = params.getAll('size');
  const [priceMin, setPriceMin] = useState(params.get('price_min') ?? '');
  const [priceMax, setPriceMax] = useState(params.get('price_max') ?? '');

  const hasActiveFilters =
    selectedSizes.length > 0 || params.has('price_min') || params.has('price_max');

  const toggleSize = (value: string) => {
    push((next) => {
      const current = next.getAll('size');
      next.delete('size');
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      for (const v of updated) next.append('size', v);
    });
  };

  const applyPrice = () => {
    push((next) => {
      if (priceMin) next.set('price_min', String(Math.max(0, Number(priceMin) * 100)));
      else next.delete('price_min');
      if (priceMax) next.set('price_max', String(Math.max(0, Number(priceMax) * 100)));
      else next.delete('price_max');
    });
  };

  const clearAll = () => {
    setPriceMin('');
    setPriceMax('');
    push((next) => {
      next.delete('size');
      next.delete('price_min');
      next.delete('price_max');
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {hasActiveFilters && (
        <button
          type="button"
          onClick={clearAll}
          className="self-start text-sm font-medium text-primary hover:underline"
        >
          Limpar filtros
        </button>
      )}

      {show.category && categoryLinks.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-semibold">Categorias</legend>
          <ul className="flex flex-col gap-1">
            {categoryLinks.map((c) => (
              <li key={c.path}>
                <Link
                  href={`/categoria/${c.path}`}
                  className={`block rounded-card px-2 py-1 text-sm hover:bg-bg-subtle ${
                    c.active ? 'font-semibold text-primary' : 'text-text'
                  }`}
                >
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      {show.price && (
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-semibold">Faixa de preço</legend>
        <p className="text-xs text-text-muted">
          Entre {formatBRL(facets.price.min)} e {formatBRL(facets.price.max)}
        </p>
        <div className="flex items-center gap-2">
          <label className="flex-1">
            <span className="sr-only">Preço mínimo (R$)</span>
            <input
              type="number"
              inputMode="numeric"
              min={0}
              placeholder="mín"
              value={priceMin}
              onChange={(e) => setPriceMin(e.target.value)}
              className="min-h-touch w-full rounded-card border border-surface-border bg-surface px-2 text-sm"
            />
          </label>
          <span aria-hidden="true" className="text-text-muted">
            –
          </span>
          <label className="flex-1">
            <span className="sr-only">Preço máximo (R$)</span>
            <input
              type="number"
              inputMode="numeric"
              min={0}
              placeholder="máx"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value)}
              className="min-h-touch w-full rounded-card border border-surface-border bg-surface px-2 text-sm"
            />
          </label>
        </div>
        <Button size="sm" variant="outline" onClick={applyPrice} className="self-start">
          Aplicar preço
        </Button>
      </fieldset>
      )}

      {show.size && facets.sizes.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-semibold">Tamanho</legend>
          <ul className="flex flex-col gap-1.5">
            {facets.sizes.map((size) => {
              const checked = selectedSizes.includes(size.value);
              return (
                <li key={size.value}>
                  <label className="flex min-h-touch cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSize(size.value)}
                      className="h-4 w-4 rounded border-surface-border"
                    />
                    <span className="flex-1">{size.value}</span>
                    <span className="text-xs text-text-muted">({size.count})</span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>
      )}
    </div>
  );
}

/** Botão + Drawer para filtros no mobile. */
export function PlpFiltersDrawer({ facets, show, categoryLinks }: PlpFiltersProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="lg:hidden">
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Filtrar
      </Button>
      <Drawer open={open} onClose={() => setOpen(false)} side="left" title="Filtros" labelledById="plp-filtros-title">
        <PlpFilters facets={facets} show={show} categoryLinks={categoryLinks} />
      </Drawer>
    </div>
  );
}
