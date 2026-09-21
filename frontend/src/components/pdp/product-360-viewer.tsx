'use client';

import { useMemo, useRef, useState } from 'react';
import type { ProductImage } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { PRODUCT_360_MIN_IMAGES } from '@/components/pdp/product-360-config';

interface Props {
  images: ProductImage[];
  /** Sequência pronta (fotos + quadros gerados por IA) -- quando presente,
   * usada no lugar de `images`. Ver `product_360_enabled` em Aparência. */
  spinFrames?: string[];
  productName: string;
}

const DRAG_PX_PER_FRAME = 18;

/**
 * Giro 360° a partir das fotos já cadastradas do produto, enriquecido com
 * quadros intermediários gerados por IA (RIFE) entre pares de ângulo
 * parecido quando disponíveis (`spinFrames`) -- sem isso, cai pra troca
 * direta entre as fotos originais. Arrastar troca de quadro conforme a
 * distância percorrida, dando a sensação de girar o produto; duplo
 * clique/toque aplica um zoom simples no quadro atual.
 */
export function Product360Viewer({ images, spinFrames, productName }: Props) {
  const frames = useMemo(() => {
    if (spinFrames && spinFrames.length > 0) return spinFrames;
    // mesma ordem que a galeria mostra (a API já traz a primária primeiro)
    return images.map((img) => resolveMediaUrl(img.zoom_url)).filter((url): url is string => Boolean(url));
  }, [images, spinFrames]);

  const [index, setIndex] = useState(0);
  const [zoomed, setZoomed] = useState(false);
  const [hintVisible, setHintVisible] = useState(true);
  const dragging = useRef(false);
  const startX = useRef(0);
  const startIndex = useRef(0);
  const moved = useRef(false);

  if (frames.length < PRODUCT_360_MIN_IMAGES) return null;

  const wrap = (i: number): number => ((i % frames.length) + frames.length) % frames.length;

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>): void {
    dragging.current = true;
    moved.current = false;
    startX.current = e.clientX;
    startIndex.current = index;
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>): void {
    if (!dragging.current) return;
    const dx = e.clientX - startX.current;
    if (Math.abs(dx) > 4) {
      moved.current = true;
      setHintVisible(false);
    }
    const delta = Math.round(dx / DRAG_PX_PER_FRAME);
    setIndex(wrap(startIndex.current - delta));
  }

  function onPointerUp(): void {
    dragging.current = false;
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className={`relative aspect-square w-full max-w-sm touch-none select-none overflow-hidden rounded-card border border-surface-border bg-white ${
          zoomed ? 'cursor-zoom-out' : 'cursor-grab active:cursor-grabbing'
        }`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onPointerLeave={onPointerUp}
        onDoubleClick={() => setZoomed((z) => !z)}
      >
        {/* pré-carrega os outros quadros pra arrastar sem "piscar" */}
        <div aria-hidden="true" className="hidden">
          {frames.map((src) => (
            <img key={src} src={src} alt="" />
          ))}
        </div>
        <img
          src={frames[index]}
          alt={`${productName} — vista em 360°, quadro ${index + 1} de ${frames.length}`}
          draggable={false}
          className={`h-full w-full object-contain transition-transform duration-150 ${zoomed ? 'scale-150' : ''}`}
        />
        {hintVisible && (
          <div className="pointer-events-none absolute inset-x-0 bottom-2 flex justify-center px-2">
            <span className="rounded-full bg-black/60 px-3 py-1 text-center text-xs font-medium text-white">
              ↔ Arraste para girar · toque 2x para dar zoom
            </span>
          </div>
        )}
      </div>
      <div className="flex gap-1" role="presentation">
        {frames.map((_, i) => (
          <span
            key={i}
            className={`h-1.5 w-1.5 rounded-full transition-colors ${i === index ? 'bg-primary' : 'bg-surface-border'}`}
          />
        ))}
      </div>
    </div>
  );
}
