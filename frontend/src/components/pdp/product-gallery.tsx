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
 *   imagem principal. Zoom só NO CLIQUE (hover mostra a lupa); com o zoom, o
 *   mouse "arrasta" a imagem. Clicar de novo / tirar o cursor sai do zoom.
 * - Mobile: quadro fixo, a imagem TROCA no swipe (infinito, fade). Dois toques
 *   na imagem abrem o zoom (arrasta pra navegar); dois toques nela de novo ou
 *   um toque fora da imagem fecham. + bolinhas de paginação.
 */
export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [origin, setOrigin] = useState('50% 50%');
  const [mobileIndex, setMobileIndex] = useState(0);
  const [mobileZoom, setMobileZoom] = useState(false);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const tapRef = useRef<{ x: number; y: number; t: number } | null>(null);
  const lastTapRef = useRef(0);
  const panStartRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

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

  const mobileImg = images[mobileIndex] as ProductImage;
  const mobileZoomSrc =
    resolveMediaUrl(mobileImg?.zoom_url) ?? resolveMediaUrl(mobileImg?.medium_url) ?? '';

  const go = (delta: number) => {
    setZoom(false);
    setIndex((i) => (i + delta + images.length) % images.length);
  };
  const goMobile = (delta: number) =>
    setMobileIndex((i) => (i + delta + images.length) % images.length);

  const closeMobileZoom = () => {
    setMobileZoom(false);
    setPan({ x: 0, y: 0 });
  };

  const onMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    setOrigin(`${x}% ${y}%`);
  };

  // --- gestos do quadro mobile (não ampliado): swipe troca / 2 toques ampliam
  const onFrameTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (t) tapRef.current = { x: t.clientX, y: t.clientY, t: Date.now() };
  };
  const onFrameTouchEnd = (e: React.TouchEvent) => {
    const start = tapRef.current;
    tapRef.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    const moved = Math.hypot(dx, dy);
    const now = Date.now();

    if (moved < 12) {
      if (now - lastTapRef.current < 300) {
        lastTapRef.current = 0;
        setPan({ x: 0, y: 0 });
        setMobileZoom(true);
      } else {
        lastTapRef.current = now;
      }
      return;
    }
    if (images.length > 1 && Math.abs(dx) >= 40 && Math.abs(dx) > Math.abs(dy)) {
      goMobile(dx < 0 ? 1 : -1);
    }
  };

  // --- gestos com o zoom mobile aberto: arrasta pra navegar / 2 toques fecham
  const onZoomTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    tapRef.current = { x: t.clientX, y: t.clientY, t: Date.now() };
    panStartRef.current = { x: t.clientX, y: t.clientY, px: pan.x, py: pan.y };
  };
  const onZoomTouchMove = (e: React.TouchEvent) => {
    const t = e.touches[0];
    const s = panStartRef.current;
    if (!t || !s) return;
    setPan({ x: s.px + (t.clientX - s.x), y: s.py + (t.clientY - s.y) });
  };
  const onZoomTouchEnd = (e: React.TouchEvent) => {
    const start = tapRef.current;
    tapRef.current = null;
    panStartRef.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    if (!t) return;
    const moved = Math.hypot(t.clientX - start.x, t.clientY - start.y);
    if (moved >= 12) return; // foi arrasto (pan), não toque
    const now = Date.now();
    if (now - lastTapRef.current < 300) {
      lastTapRef.current = 0;
      closeMobileZoom();
    } else {
      lastTapRef.current = now;
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Desktop: miniaturas à esquerda + imagem principal */}
      <div className="hidden md:flex md:gap-3">
        {images.length > 1 && (
          <ul
            className="flex max-h-[520px] flex-col gap-2 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            aria-label="Miniaturas do produto"
          >
            {images.map((image, i) => {
              const thumb = resolveMediaUrl(image.thumb_url);
              const selected = i === safeIndex;
              return (
                <li key={image.id} className="relative pr-3.5">
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
                      className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-text"
                      style={{
                        width: 0,
                        height: 0,
                        borderTop: '9px solid transparent',
                        borderBottom: '9px solid transparent',
                        borderLeft: '11px solid currentColor',
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

      {/* Mobile: quadro fixo; imagem troca no swipe; 2 toques = zoom */}
      <div
        className="relative h-[min(88vw,58vh)] w-full overflow-hidden rounded-card border border-surface-border bg-bg-subtle md:hidden"
        onTouchStart={onFrameTouchStart}
        onTouchEnd={onFrameTouchEnd}
        role="img"
        aria-label={`${productName} — imagem ${mobileIndex + 1} de ${images.length}`}
      >
        {images.map((image, i) => (
          <Image
            key={image.id}
            src={resolveMediaUrl(image.medium_url) ?? ''}
            alt={image.alt ?? `${productName} — imagem ${i + 1}`}
            fill
            sizes="100vw"
            priority={i === 0}
            className={`object-cover transition-opacity duration-200 ${
              i === mobileIndex ? 'opacity-100' : 'opacity-0'
            }`}
          />
        ))}
      </div>
      {images.length > 1 && (
        <div className="flex justify-center gap-2 md:hidden" role="tablist" aria-label="Fotos do produto">
          {images.map((image, i) => (
            <button
              key={image.id}
              type="button"
              role="tab"
              aria-selected={i === mobileIndex}
              aria-label={`Ir para a foto ${i + 1}`}
              onClick={() => setMobileIndex(i)}
              className={`h-2 rounded-full transition-all ${
                i === mobileIndex ? 'w-4 bg-btn' : 'w-2 bg-surface-border'
              }`}
            />
          ))}
        </div>
      )}

      {/* Zoom mobile — overlay: arrasta pra navegar; toque fora / 2 toques na
          imagem fecham */}
      {mobileZoom && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-black/90 md:hidden"
          onClick={closeMobileZoom}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={mobileZoomSrc}
            alt=""
            draggable={false}
            onClick={(e) => e.stopPropagation()}
            onTouchStart={onZoomTouchStart}
            onTouchMove={onZoomTouchMove}
            onTouchEnd={onZoomTouchEnd}
            className="h-auto w-[185%] max-w-none select-none"
            style={{ transform: `translate3d(${pan.x}px, ${pan.y}px, 0)`, touchAction: 'none' }}
          />
        </div>
      )}
    </div>
  );
}
