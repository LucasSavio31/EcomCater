'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProductListItem } from '@/modules/catalog/types';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';
import { ProductCard } from './product-card';

interface ProductCarouselProps {
  products: ProductListItem[];
  ariaLabel: string;
  /** Lista de origem (GA4 `select_item`). */
  listId?: string;
  listName?: string;
  /**
   * Loop infinito (padrão): ao chegar no fim volta pro começo sem emenda.
   * Precisa de pelo menos 3 itens; abaixo disso vira carrossel comum.
   */
  loop?: boolean;
}

/**
 * Carrossel horizontal com scroll-snap + setas (desktop).
 * Loop: renderiza a lista 3x e, quando o scroll para perto de uma borda, salta
 * uma "cópia" inteira de volta ao centro — como o conteúdo é idêntico, a volta
 * é invisível e o usuário rola pra sempre nos dois sentidos.
 */
export function ProductCarousel({
  products,
  ariaLabel,
  listId,
  listName,
  loop = true,
}: ProductCarouselProps) {
  const trackRef = useRef<HTMLUListElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const looping = loop && products.length >= 3;
  const slides = looping
    ? [0, 1, 2].flatMap((copy) => products.map((p) => ({ p, copy })))
    : products.map((p) => ({ p, copy: 0 }));

  const updateEdges = useCallback(() => {
    const el = trackRef.current;
    if (!el || looping) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  }, [looping]);

  const normalize = useCallback(() => {
    const el = trackRef.current;
    if (!el || !looping) return;
    const copy = el.scrollWidth / 3;
    if (copy <= 0) return;
    if (el.scrollLeft < copy * 0.5) el.scrollLeft += copy;
    else if (el.scrollLeft > copy * 1.5) el.scrollLeft -= copy;
  }, [looping]);

  // posiciona na cópia central ao montar / trocar a lista (instantâneo)
  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    if (looping) el.scrollLeft = el.scrollWidth / 3;
    updateEdges();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [looping, products]);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    let idle: number | undefined;
    const onScroll = () => {
      updateEdges();
      if (!looping) return;
      window.clearTimeout(idle);
      idle = window.setTimeout(normalize, 120); // só normaliza quando o scroll para
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', updateEdges);
    return () => {
      window.clearTimeout(idle);
      el.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', updateEdges);
    };
  }, [updateEdges, normalize, looping]);

  const step = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.round(el.clientWidth * 0.9), behavior: 'smooth' });
  };

  if (products.length === 0) return null;

  return (
    <div className="relative" role="group" aria-label={ariaLabel}>
      <button
        type="button"
        onClick={() => step(-1)}
        disabled={!looping && atStart}
        aria-label="Anterior"
        className="absolute -left-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm disabled:opacity-0 lg:block"
      >
        <ChevronLeftIcon className="h-5 w-5" />
      </button>
      <ul
        ref={trackRef}
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 lg:gap-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {slides.map(({ p, copy }, i) => (
          <li
            key={`${p.id}-${copy}`}
            className="w-[46%] shrink-0 snap-start sm:w-[38%] md:w-[30%] lg:w-[23%]"
            aria-hidden={looping && copy !== 1 ? true : undefined}
          >
            <ProductCard
              product={p}
              className="h-full"
              listId={listId}
              listName={listName ?? ariaLabel}
              index={i % products.length}
            />
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => step(1)}
        disabled={!looping && atEnd}
        aria-label="Próximo"
        className="absolute -right-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm disabled:opacity-0 lg:block"
      >
        <ChevronRightIcon className="h-5 w-5" />
      </button>
    </div>
  );
}
