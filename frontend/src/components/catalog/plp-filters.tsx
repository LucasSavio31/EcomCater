'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Button, Drawer } from '@ecom/ui';
import type { ProductFacets, SizeFacet } from '@/modules/catalog/types';
import { formatBRL } from '@/lib/format';

export interface FilterVisibility {
  size: boolean;
  price: boolean;
  category: boolean;
  color: boolean;
  material: boolean;
}

const ALL_VISIBLE: FilterVisibility = {
  size: true,
  price: true,
  category: true,
  color: true,
  material: true,
};

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

/** Formulário de filtros (categoria + preço + tamanho + cor + material). Reflete e altera a URL. */
export function PlpFilters({ facets, show = ALL_VISIBLE, categoryLinks = [] }: PlpFiltersProps) {
  const { params, push } = useFilterActions();

  // faixa de preço (em centavos) — barra deslizante
  const bounds = {
    min: facets.price.min,
    max: Math.max(facets.price.max, facets.price.min + 1),
  };
  const step = Math.max(100, Math.ceil((bounds.max - bounds.min) / 200 / 100) * 100);
  const clampLo = (v: number) => Math.min(Math.max(v, bounds.min), bounds.max);
  const [lo, setLo] = useState(() => clampLo(Number(params.get('price_min')) || bounds.min));
  const [hi, setHi] = useState(() => {
    const raw = Number(params.get('price_max'));
    return raw > 0 ? Math.min(raw, bounds.max) : bounds.max;
  });

  const commitPrice = (nlo: number, nhi: number) => {
    push((next) => {
      if (nlo > bounds.min) next.set('price_min', String(nlo));
      else next.delete('price_min');
      if (nhi < bounds.max) next.set('price_max', String(nhi));
      else next.delete('price_max');
    });
  };

  const MULTI_KEYS = ['size', 'material', 'color'] as const;
  const hasActiveFilters =
    MULTI_KEYS.some((k) => params.getAll(k).length > 0) ||
    params.has('price_min') ||
    params.has('price_max');

  const toggleMulti = (key: string, value: string) => {
    push((next) => {
      const current = next.getAll(key);
      next.delete(key);
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      for (const v of updated) next.append(key, v);
    });
  };

  const clearAll = () => {
    setLo(bounds.min);
    setHi(bounds.max);
    push((next) => {
      for (const k of MULTI_KEYS) next.delete(k);
      next.delete('price_min');
      next.delete('price_max');
    });
  };

  const CheckGroup = ({
    title,
    urlKey,
    items,
    boxes = false,
  }: {
    title: string;
    urlKey: string;
    items: SizeFacet[];
    boxes?: boolean;
  }) => {
    if (items.length === 0) return null;
    const selected = params.getAll(urlKey);
    return (
      <fieldset className="flex flex-col gap-2 border-t border-surface-border pt-4 first:border-0 first:pt-0">
        <legend className="mb-1 text-sm font-semibold">{title}</legend>
        {boxes ? (
          <div className="flex flex-wrap gap-2">
            {items.map((it) => {
              const checked = selected.includes(it.value);
              return (
                <button
                  key={it.value}
                  type="button"
                  aria-pressed={checked}
                  onClick={() => toggleMulti(urlKey, it.value)}
                  className={`flex h-10 min-w-[3rem] items-center justify-center rounded-card border-2 px-3 text-sm font-medium ${
                    checked
                      ? 'border-var-border bg-var text-var-fg'
                      : 'border-surface-border hover:border-var-border'
                  }`}
                >
                  {it.value}
                </button>
              );
            })}
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {items.map((it) => {
              const checked = selected.includes(it.value);
              return (
                <li key={it.value}>
                  <label className="flex min-h-touch cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleMulti(urlKey, it.value)}
                      className="h-4 w-4 rounded border-surface-border"
                    />
                    <span className="flex-1">{it.value}</span>
                    <span className="text-xs text-text-muted">({it.count})</span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </fieldset>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      {show.price && bounds.max > bounds.min && (
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1 text-sm font-semibold">Faixa de preço</legend>
          <p className="text-sm">
            <span className="font-medium">{formatBRL(lo)}</span>
            <span className="text-text-muted"> – </span>
            <span className="font-medium">{formatBRL(hi)}</span>
          </p>

          <div className="relative h-5 select-none">
            <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-surface-border" />
            <div
              className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-primary"
              style={{
                left: `${((lo - bounds.min) / (bounds.max - bounds.min)) * 100}%`,
                right: `${100 - ((hi - bounds.min) / (bounds.max - bounds.min)) * 100}%`,
              }}
            />
            {(
              [
                ['Preço mínimo', lo, (v: number) => {
                  const n = Math.min(v, hi - step);
                  setLo(n);
                  return n;
                }, (n: number) => commitPrice(n, hi)],
                ['Preço máximo', hi, (v: number) => {
                  const n = Math.max(v, lo + step);
                  setHi(n);
                  return n;
                }, (n: number) => commitPrice(lo, n)],
              ] as const
            ).map(([label, value, onDrag, onCommit], i) => (
              <input
                key={i}
                type="range"
                aria-label={label}
                min={bounds.min}
                max={bounds.max}
                step={step}
                value={value}
                onChange={(e) => onDrag(Number(e.target.value))}
                onPointerUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
                onKeyUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
                onTouchEnd={(e) => onCommit(Number((e.target as HTMLInputElement).value))}
                className={[
                  'pointer-events-none absolute inset-x-0 top-1/2 h-0 w-full -translate-y-1/2 appearance-none bg-transparent',
                  '[&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
                  '[&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full',
                  '[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow',
                  '[&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4',
                  '[&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:rounded-full',
                  '[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:bg-white',
                ].join(' ')}
              />
            ))}
          </div>
        </fieldset>
      )}

      {hasActiveFilters && (
        <button
          type="button"
          onClick={clearAll}
          className="w-full rounded-btn border-2 border-primary px-4 py-2 text-sm font-bold uppercase tracking-wide text-primary hover:bg-primary hover:text-primary-fg"
        >
          Limpar tudo
        </button>
      )}

      {show.category && categoryLinks.length > 0 && (
        <fieldset className="flex flex-col gap-2 border-t border-surface-border pt-4">
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

      {show.color && <CheckGroup title="Cor" urlKey="color" items={facets.colors} />}
      {show.material && (
        <CheckGroup title="Material" urlKey="material" items={facets.materials} />
      )}
      {show.size && <CheckGroup title="Tamanho" urlKey="size" items={facets.sizes} boxes />}
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
