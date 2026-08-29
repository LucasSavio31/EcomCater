'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProductListItem } from '@/modules/catalog/types';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';
import { ProductCard } from './product-card';

interface ProductCarouselProps {
  products: ProductListItem[];
  ariaLabel: string;
}

/** Carrossel horizontal com scroll-snap + setas (desktop). Teclado: setas nativas do scroll. */
export function ProductCarousel({ products, ariaLabel }: ProductCarouselProps) {
  const trackRef = useRef<HTMLUListElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const updateEdges = useCallback(() => {
    const el = trackRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    updateEdges();
    const el = trackRef.current;
    if (!el) return;
    el.addEventListener('scroll', updateEdges, { passive: true });
    window.addEventListener('resize', updateEdges);
    return () => {
      el.removeEventListener('scroll', updateEdges);
      window.removeEventListener('resize', updateEdges);
    };
  }, [updateEdges]);

  const scrollBy = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.round(el.clientWidth * 0.9), behavior: 'smooth' });
  };

  if (products.length === 0) return null;

  return (
    <div className="relative" role="group" aria-label={ariaLabel}>
      <button
        type="button"
        onClick={() => scrollBy(-1)}
        disabled={atStart}
        aria-label="Anterior"
        className="absolute -left-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm disabled:opacity-0 lg:block"
      >
        <ChevronLeftIcon className="h-5 w-5" />
      </button>
      <ul
        ref={trackRef}
        className="flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth pb-2 lg:gap-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {products.map((product) => (
          <li
            key={product.id}
            className="w-[46%] shrink-0 snap-start sm:w-[38%] md:w-[30%] lg:w-[23%]"
          >
            <ProductCard product={product} className="h-full" />
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => scrollBy(1)}
        disabled={atEnd}
        aria-label="Próximo"
        className="absolute -right-3 top-1/2 z-10 hidden -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm disabled:opacity-0 lg:block"
      >
        <ChevronRightIcon className="h-5 w-5" />
      </button>
    </div>
  );
}
