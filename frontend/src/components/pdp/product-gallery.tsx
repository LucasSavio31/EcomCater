'use client';

import { useRef, useState } from 'react';
import Image from 'next/image';
import type { ProductImage } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';

interface ProductGalleryProps {
  images: ProductImage[];
  productName: string;
}

/**
 * Galeria da PDP.
 * - Desktop: coluna de miniaturas À ESQUERDA (com uma seta na selecionada) +
 *   imagem principal. O zoom só entra NO CLIQUE: ao passar o cursor aparece a
 *   lupa (`cursor: zoom-in`); clicando, a imagem amplia e o mouse passa a
 *   "arrastar" o produto (pan via `background-position`). Clicar de novo — ou
 *   tirar o cursor — sai do zoom.
 * - Mobile: carrossel com scroll-snap.
 */
export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [origin, setOrigin] = useState('50% 50%');
  const trackRef = useRef<HTMLDivElement>(null);

  if (images.length === 0) {
    return (
      <div className="flex aspect-square items-center justify-center rounded-card bg-bg-subtle text-sm text-text-muted">
        Sem imagem
      </div>
    );
  }

  const safeIndex = Math.min(index, images.length - 1);
  const current = images[safeIndex] as ProductImage;
  const mainSrc = resolveMediaUrl(current.medium_url) ?? '';
  const zoomSrc = resolveMediaUrl(current.zoom_url) ?? mainSrc;

  const go = (delta: number) => {
    setZoom(false);
    setIndex((i) => (i + delta + images.length) % images.length);
  };

  const onMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    setOrigin(`${x}% ${y}%`);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Desktop: miniaturas à esquerda + imagem principal */}
      <div className="hidden md:flex md:gap-3">
        {images.length > 1 && (
          <ul
            className="flex max-h-[520px] flex-col gap-2 overflow-y-auto pr-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            aria-label="Miniaturas do produto"
          >
            {images.map((image, i) => {
              const thumb = resolveMediaUrl(image.thumb_url);
              const selected = i === safeIndex;
              return (
                <li key={image.id} className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setZoom(false);
                      setIndex(i);
                    }}
                    aria-label={`Ver imagem ${i + 1}`}
                    aria-current={selected ? 'true' : undefined}
                    className={`relative block h-20 w-20 shrink-0 overflow-hidden rounded-card border-2 transition ${
                      selected ? 'border-primary' : 'border-surface-border hover:border-primary/60'
                    }`}
                  >
                    {thumb && <Image src={thumb} alt="" fill sizes="80px" className="object-cover" />}
                  </button>
                  {selected && (
                    <span
                      aria-hidden
                      className="pointer-events-none absolute -right-2 top-1/2 -translate-y-1/2 text-text"
                      style={{
                        width: 0,
                        height: 0,
                        borderTop: '8px solid transparent',
                        borderBottom: '8px solid transparent',
                        borderLeft: '10px solid currentColor',
                      }}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        )}

        <div className="relative min-w-0 flex-1">
          <div
            className={`relative aspect-square w-full overflow-hidden rounded-card border border-surface-border bg-bg-subtle ${
              zoom ? 'cursor-zoom-out' : 'cursor-zoom-in'
            }`}
            onMouseLeave={() => setZoom(false)}
            onMouseMove={onMove}
            onClick={() => setZoom((z) => !z)}
            role="img"
            aria-label={`${productName} — imagem ${safeIndex + 1} de ${images.length}`}
          >
            <Image
              src={mainSrc}
              alt={current.alt ?? productName}
              fill
              sizes="(min-width: 1024px) 40vw, 60vw"
              priority
              className={zoom ? 'opacity-0' : 'object-cover'}
            />
            {zoom && (
              <div
                className="absolute inset-0 bg-surface bg-no-repeat"
                style={{
                  backgroundImage: `url(${zoomSrc})`,
                  backgroundSize: '220%',
                  backgroundPosition: origin,
                }}
              />
            )}
          </div>
          {images.length > 1 && !zoom && (
            <>
              <button
                type="button"
                onClick={() => go(-1)}
                aria-label="Imagem anterior"
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm"
              >
                <ChevronLeftIcon className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => go(1)}
                aria-label="Próxima imagem"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full border border-surface-border bg-surface p-2 shadow-sm"
              >
                <ChevronRightIcon className="h-5 w-5" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Carrossel (mobile) — altura limitada p/ preço + numeração + Comprar
          entrarem na dobra */}
      <div
        ref={trackRef}
        className="flex snap-x snap-mandatory gap-2 overflow-x-auto rounded-card md:hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {images.map((image, i) => {
          const src = resolveMediaUrl(image.medium_url) ?? '';
          return (
            <div
              key={image.id}
              className="relative h-[min(88vw,58vh)] w-full shrink-0 snap-center overflow-hidden rounded-card border border-surface-border bg-bg-subtle"
            >
              <Image
                src={src}
                alt={image.alt ?? `${productName} — imagem ${i + 1}`}
                fill
                sizes="100vw"
                priority={i === 0}
                className="object-cover"
              />
            </div>
          );
        })}
      </div>
      {images.length > 1 && (
        <p className="text-center text-xs text-text-muted md:hidden" aria-hidden>
          {images.length} fotos — arraste para o lado
        </p>
      )}
    </div>
  );
}
