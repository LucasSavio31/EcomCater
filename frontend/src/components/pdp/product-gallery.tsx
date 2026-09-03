'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import type { ProductImage } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { ChevronLeftIcon, ChevronRightIcon, SearchIcon } from '@/components/icons';

interface ProductGalleryProps {
  images: ProductImage[];
  productName: string;
}

/**
 * Galeria da PDP.
 * - Desktop: coluna de miniaturas À ESQUERDA + imagem principal. Zoom só NO
 *   CLIQUE (hover = lupa); com o zoom, o mouse "arrasta" a imagem.
 * - Mobile: carrossel deslizante infinito (a imagem "anda" de um lado pro
 *   outro no swipe) + bolinhas. Ícone de lupa discreto no topo e/ou 2 toques
 *   abrem o zoom; arrasta pra navegar; 2 toques na imagem ou toque fora fecham.
 */
export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [origin, setOrigin] = useState('50% 50%');

  const [mobileIndex, setMobileIndex] = useState(0);
  const [pos, setPos] = useState(1); // posição na faixa (slides reais em 1..N; clones em 0 e N+1)
  const [dragX, setDragX] = useState(0);
  const [animate, setAnimate] = useState(true);

  const [mobileZoom, setMobileZoom] = useState(false);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const frameRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ x: number; y: number; dragging: boolean } | null>(null);
  const lastTapRef = useRef(0);
  const panStartRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  // reativa a transição depois do "pulo" invisível de wrap (nunca durante o arrasto)
  useEffect(() => {
    if (animate || dragRef.current) return;
    const id = requestAnimationFrame(() => setAnimate(true));
    return () => cancelAnimationFrame(id);
  }, [animate]);

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

  const loopMobile = images.length > 1;
  const slides: ProductImage[] = loopMobile
    ? [images[images.length - 1] as ProductImage, ...images, images[0] as ProductImage]
    : images;

  const go = (delta: number) => {
    setZoom(false);
    setIndex((i) => (i + delta + images.length) % images.length);
  };

  const stepMobile = (dir: 1 | -1) => {
    setMobileIndex((i) => (i + dir + images.length) % images.length);
    setPos((p) => p + dir);
    setDragX(0);
    setAnimate(true);
  };
  const goToMobile = (i: number) => {
    setMobileIndex(i);
    setPos(i + 1);
    setDragX(0);
    setAnimate(true);
  };
  const onTrackTransitionEnd = () => {
    if (!loopMobile) return;
    if (pos === 0) {
      setAnimate(false);
      setPos(images.length);
    } else if (pos === images.length + 1) {
      setAnimate(false);
      setPos(1);
    }
  };

  const openMobileZoom = () => {
    setPan({ x: 0, y: 0 });
    setMobileZoom(true);
  };
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

  // --- gestos do carrossel mobile (fechado): arrasta a faixa / 2 toques = zoom
  const onFrameTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    dragRef.current = { x: t.clientX, y: t.clientY, dragging: false };
    setAnimate(false);
  };
  const onFrameTouchMove = (e: React.TouchEvent) => {
    const d = dragRef.current;
    const t = e.touches[0];
    if (!d || !t) return;
    const dx = t.clientX - d.x;
    const dy = t.clientY - d.y;
    if (!d.dragging && Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) d.dragging = true;
    if (d.dragging) setDragX(dx);
  };
  const onFrameTouchEnd = (e: React.TouchEvent) => {
    const d = dragRef.current;
    dragRef.current = null;
    if (!d) return;
    const t = e.changedTouches[0];
    const dx = t ? t.clientX - d.x : 0;

    if (!d.dragging) {
      setAnimate(true);
      setDragX(0);
      const now = Date.now();
      if (now - lastTapRef.current < 300) {
        lastTapRef.current = 0;
        openMobileZoom();
      } else {
        lastTapRef.current = now;
      }
      return;
    }
    const w = frameRef.current?.clientWidth ?? 1;
    if (loopMobile && dx <= -w * 0.2) stepMobile(1);
    else if (loopMobile && dx >= w * 0.2) stepMobile(-1);
    else {
      setAnimate(true);
      setDragX(0);
    }
  };

  // --- gestos com o zoom mobile aberto: arrasta pra navegar / 2 toques fecham
  const onZoomTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    dragRef.current = { x: t.clientX, y: t.clientY, dragging: false };
    panStartRef.current = { x: t.clientX, y: t.clientY, px: pan.x, py: pan.y };
  };
  const onZoomTouchMove = (e: React.TouchEvent) => {
    const t = e.touches[0];
    const s = panStartRef.current;
    const d = dragRef.current;
    if (!t || !s || !d) return;
    if (Math.hypot(t.clientX - s.x, t.clientY - s.y) > 10) d.dragging = true;
    setPan({ x: s.px + (t.clientX - s.x), y: s.py + (t.clientY - s.y) });
  };
  const onZoomTouchEnd = () => {
    const d = dragRef.current;
    dragRef.current = null;
    panStartRef.current = null;
    if (!d || d.dragging) return;
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

      {/* Mobile: carrossel deslizante (a imagem "anda" no swipe) */}
      <div
        ref={frameRef}
        className="relative h-[min(88vw,58vh)] w-full overflow-hidden rounded-card border border-surface-border bg-bg-subtle md:hidden"
        style={{ touchAction: 'pan-y' }}
        onTouchStart={onFrameTouchStart}
        onTouchMove={onFrameTouchMove}
        onTouchEnd={onFrameTouchEnd}
        role="img"
        aria-label={`${productName} — imagem ${mobileIndex + 1} de ${images.length}`}
      >
        <div
          className="flex h-full w-full"
          onTransitionEnd={onTrackTransitionEnd}
          style={{
            transform: `translate3d(calc(${-100 * (loopMobile ? pos : 0)}% + ${dragX}px), 0, 0)`,
            transition: animate ? 'transform 300ms ease-out' : 'none',
          }}
        >
          {slides.map((image, i) => (
            <div key={`${image.id}-${i}`} className="relative h-full w-full shrink-0">
              <Image
                src={resolveMediaUrl(image.medium_url) ?? ''}
                alt={image.alt ?? productName}
                fill
                sizes="100vw"
                priority={i <= 1}
                className="object-cover"
                draggable={false}
              />
            </div>
          ))}
        </div>

        {/* lupa discreta */}
        <button
          type="button"
          onClick={openMobileZoom}
          aria-label="Ampliar imagem"
          className="absolute right-2 top-2 z-10 rounded-full bg-black/30 p-1.5 text-white backdrop-blur-sm active:bg-black/50"
        >
          <SearchIcon className="h-4 w-4" />
        </button>
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
              onClick={() => goToMobile(i)}
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
