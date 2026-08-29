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
 * - Desktop: coluna de thumbnails + imagem principal com setas e zoom (lente que
 *   segue o cursor, usando `background-position` na imagem em resolução `zoom`).
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
    <div className="flex flex-col gap-3 md:flex-row md:gap-4">
      {/* Thumbnails (desktop) */}
      {images.length > 1 && (
        <ul className="hidden shrink-0 flex-col gap-2 md:flex" aria-label="Miniaturas do produto">
          {images.map((image, i) => {
            const thumb = resolveMediaUrl(image.thumb_url);
            return (
              <li key={image.id}>
                <button
                  type="button"
                  onClick={() => {
                    setZoom(false);
                    setIndex(i);
                  }}
                  aria-label={`Ver imagem ${i + 1}`}
                  aria-current={i === safeIndex ? 'true' : undefined}
                  className={`relative block h-16 w-16 overflow-hidden rounded-card border ${
                    i === safeIndex ? 'border-primary' : 'border-surface-border'
                  }`}
                >
                  {thumb && <Image src={thumb} alt="" fill sizes="64px" className="object-cover" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {/* Imagem principal (desktop) */}
      <div className="relative hidden flex-1 md:block">
        <div
          className="relative aspect-square w-full cursor-zoom-in overflow-hidden rounded-card border border-surface-border bg-bg-subtle"
          onMouseEnter={() => setZoom(true)}
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
            className={zoom ? 'opacity-0' : 'object-contain'}
          />
          {zoom && (
            <div
              className="absolute inset-0 bg-surface bg-no-repeat"
              style={{
                backgroundImage: `url(${zoomSrc})`,
                backgroundSize: '200%',
                backgroundPosition: origin,
              }}
            />
          )}
        </div>
        {images.length > 1 && (
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

      {/* Carrossel (mobile) */}
      <div
        ref={trackRef}
        className="flex snap-x snap-mandatory gap-2 overflow-x-auto rounded-card md:hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {images.map((image, i) => {
          const src = resolveMediaUrl(image.medium_url) ?? '';
          return (
            <div
              key={image.id}
              className="relative aspect-square w-full shrink-0 snap-center overflow-hidden rounded-card border border-surface-border bg-bg-subtle"
            >
              <Image
                src={src}
                alt={image.alt ?? `${productName} — imagem ${i + 1}`}
                fill
                sizes="100vw"
                priority={i === 0}
                className="object-contain"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
