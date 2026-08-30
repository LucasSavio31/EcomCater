'use client';

import { useEffect, useRef, useState } from 'react';
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

/** Classe do <input type=range> transparente (só o thumb visível). */
const RANGE_CLS = [
  'pointer-events-none absolute inset-0 m-0 h-6 w-full cursor-pointer appearance-none bg-transparent',
  '[&::-webkit-slider-runnable-track]:h-6 [&::-webkit-slider-runnable-track]:bg-transparent',
  '[&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:mt-1 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
  '[&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full',
  '[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow',
  '[&::-moz-range-track]:h-6 [&::-moz-range-track]:bg-transparent',
  '[&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4',
  '[&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:rounded-full',
  '[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:bg-white',
].join(' ');

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

  // faixa de preço (em centavos) — barra deslizante de R$0 até o maior preço.
  // Truque do range duplo: dois valores INDEPENDENTES (a, b); a faixa exibida
  // é [min(a,b), max(a,b)]. Assim nenhum controle "briga" com o outro ao arrastar.
  const STEP = 5000; // R$ 50
  const priceMax = Math.max(Math.ceil((facets.price.max || 0) / STEP) * STEP, STEP);
  const cap = (v: number) => Math.min(Math.max(Math.round(v), 0), priceMax);
  const [a, setA] = useState(() => cap(Number(params.get('price_min')) || 0));
  const [b, setB] = useState(() => {
    const raw = Number(params.get('price_max'));
    return raw > 0 ? cap(raw) : priceMax;
  });
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);

  // reajusta ao trocar de categoria (novo teto de preço)
  useEffect(() => {
    setA((v) => cap(v));
    setB((v) => (v <= 0 || v >= priceMax ? priceMax : cap(v)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priceMax]);

  // FILTRO AUTOMÁTICO: ~350ms depois de parar de mexer, aplica na URL
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const t = setTimeout(() => {
      push((next) => {
        if (lo > 0) next.set('price_min', String(lo));
        else next.delete('price_min');
        if (hi < priceMax) next.set('price_max', String(hi));
        else next.delete('price_max');
      });
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lo, hi, priceMax]);

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
    firstRun.current = true; // não deixa o debounce re-aplicar preço logo depois
    setA(0);
    setB(priceMax);
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
      {show.price && (
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1 text-sm font-semibold">Faixa de preço</legend>
          <p className="text-sm">
            <span className="font-medium">{formatBRL(lo)}</span>
            <span className="text-text-muted"> – </span>
            <span className="font-medium">
              {formatBRL(hi)}
              {hi >= priceMax ? '+' : ''}
            </span>
          </p>

          <div className="relative h-6 select-none">
            <div className="pointer-events-none absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-surface-border" />
            <div
              className="pointer-events-none absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-primary"
              style={{
                left: `${Math.max(0, Math.min(100, (lo / priceMax) * 100))}%`,
                width: `${Math.max(0, Math.min(100, ((hi - lo) / priceMax) * 100))}%`,
              }}
            />
            <input
              type="range"
              aria-label="Preço (controle 1)"
              min={0}
              max={priceMax}
              step={STEP}
              value={a}
              onChange={(e) => setA(cap(Number(e.target.value)))}
              className={RANGE_CLS}
              style={{ zIndex: a > priceMax / 2 ? 5 : 3 }}
            />
            <input
              type="range"
              aria-label="Preço (controle 2)"
              min={0}
              max={priceMax}
              step={STEP}
              value={b}
              onChange={(e) => setB(cap(Number(e.target.value)))}
              className={RANGE_CLS}
              style={{ zIndex: 4 }}
            />
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
