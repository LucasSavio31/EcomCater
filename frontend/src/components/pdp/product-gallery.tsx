'use client';

import { useRef, useState } from 'react';
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
 * - Mobile: as fotos ficam TODAS pré-carregadas (eager) e empilhadas; o swipe
 *   faz a atual sair e a próxima entrar deslizando + fade (loop infinito por
 *   módulo). Nunca fica em branco, mesmo passando rápido. 2 toques ampliam
 *   DENTRO do quadro (arrasta pra navegar); um toque sai.
 */
export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [origin, setOrigin] = useState('50% 50%');

  const [mobileIndex, setMobileIndex] = useState(0);
  const [prevIndex, setPrevIndex] = useState<number | null>(null);
  const [slideDir, setSlideDir] = useState<1 | -1>(1);
  const [dragX, setDragX] = useState(0);

  const [mobileZoom, setMobileZoom] = useState(false);
  const [bgPos, setBgPos] = useState({ x: 50, y: 50 });

  const frameRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ x: number; y: number; dragging: boolean } | null>(null);
  const lastTapRef = useRef(0);
  const panStartRef = useRef<{ x: number; y: number; bx: number; by: number } | null>(null);

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

  const changeMobile = (dir: 1 | -1) => {
    setSlideDir(dir);
    setPrevIndex(mobileIndex);
    setMobileIndex((i) => (i + dir + images.length) % images.length);
    setDragX(0);
  };
  const goToMobile = (i: number) => {
    if (i === mobileIndex) return;
    setSlideDir(i > mobileIndex ? 1 : -1);
    setPrevIndex(mobileIndex);
    setMobileIndex(i);
    setDragX(0);
  };

  const openMobileZoom = () => {
    setBgPos({ x: 50, y: 50 });
    setMobileZoom(true);
  };
  const closeMobileZoom = () => setMobileZoom(false);

  const onMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    setOrigin(`${x}% ${y}%`);
  };

  // --- gestos do quadro mobile
  const onFrameTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    dragRef.current = { x: t.clientX, y: t.clientY, dragging: false };
    if (mobileZoom) panStartRef.current = { x: t.clientX, y: t.clientY, bx: bgPos.x, by: bgPos.y };
  };
  const onFrameTouchMove = (e: React.TouchEvent) => {
    const d = dragRef.current;
    const t = e.touches[0];
    if (!d || !t) return;
    const dx = t.clientX - d.x;
    const dy = t.clientY - d.y;
    if (!d.dragging && Math.hypot(dx, dy) > 8) d.dragging = true;

    if (mobileZoom) {
      const s = panStartRef.current;
      const el = frameRef.current;
      if (!s || !el) return;
      const nx = s.bx - (dx / el.clientWidth) * 90;
      const ny = s.by - (dy / el.clientHeight) * 90;
      setBgPos({ x: Math.min(100, Math.max(0, nx)), y: Math.min(100, Math.max(0, ny)) });
      return;
    }
    if (d.dragging && Math.abs(dx) > Math.abs(dy)) {
      setDragX(Math.max(-60, Math.min(60, dx * 0.35))); // leve resistência ao arrasto
    }
  };
  const onFrameTouchEnd = (e: React.TouchEvent) => {
    const d = dragRef.current;
    dragRef.current = null;
    panStartRef.current = null;
    if (!d) return;
    const t = e.changedTouches[0];
    const dx = t ? t.clientX - d.x : 0;
    const now = Date.now();

    if (mobileZoom) {
      if (!d.dragging) closeMobileZoom();
      return;
    }
    setDragX(0);
    if (!d.dragging) {
      if (now - lastTapRef.current < 300) {
        lastTapRef.current = 0;
        openMobileZoom();
      } else {
        lastTapRef.current = now;
      }
      return;
    }
    if (images.length > 1 && Math.abs(dx) >= 40) changeMobile(dx < 0 ? 1 : -1);
  };

  const slideStyle = (i: number): React.CSSProperties => {
    if (i === mobileIndex)
      return { opacity: 1, transform: `translate3d(${dragX}px, 0, 0)`, zIndex: 2 };
    if (i === prevIndex)
      return { opacity: 0, transform: `translate3d(${-slideDir * 16}%, 0, 0)`, zIndex: 1 };
    return { opacity: 0, transform: `translate3d(${slideDir * 16}%, 0, 0)`, zIndex: 0 };
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

      {/* Mobile: fotos empilhadas (todas eager) — swipe desliza/faz o fade */}
      <div
        ref={frameRef}
        className={`relative h-[min(88vw,58vh)] w-full overflow-hidden rounded-card border border-surface-border bg-bg-subtle md:hidden ${
          mobileZoom ? 'cursor-zoom-out' : ''
        }`}
        style={{ touchAction: mobileZoom ? 'none' : 'pan-y' }}
        onTouchStart={onFrameTouchStart}
        onTouchMove={onFrameTouchMove}
        onTouchEnd={onFrameTouchEnd}
        role="img"
        aria-label={`${productName} — imagem ${mobileIndex + 1} de ${images.length}`}
      >
        {images.map((image, i) => (
          <div
            key={image.id}
            className="absolute inset-0 transition-[opacity,transform] duration-200 ease-out"
            style={slideStyle(i)}
          >
            <Image
              src={resolveMediaUrl(image.medium_url) ?? ''}
              alt={image.alt ?? `${productName} — imagem ${i + 1}`}
              fill
              sizes="100vw"
              loading="eager"
              className="object-cover"
              draggable={false}
            />
          </div>
        ))}

        {/* camada de zoom — ampliada dentro do próprio quadro */}
        {mobileZoom && (
          <div
            className="absolute inset-0 z-20 bg-surface bg-no-repeat"
            style={{
              backgroundImage: `url(${mobileZoomSrc})`,
              backgroundSize: '230%',
              backgroundPosition: `${bgPos.x}% ${bgPos.y}%`,
            }}
          />
        )}

        {!mobileZoom && (
          <button
            type="button"
            onClick={openMobileZoom}
            aria-label="Ampliar imagem"
            className="absolute right-2 top-2 z-10 rounded-full bg-black/30 p-1.5 text-white backdrop-blur-sm active:bg-black/50"
          >
            <SearchIcon className="h-4 w-4" />
          </button>
        )}
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
    </div>
  );
}
