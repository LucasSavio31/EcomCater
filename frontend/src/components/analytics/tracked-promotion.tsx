'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { trackPromotion, type TrackPromotion } from '@/modules/analytics';

/**
 * Envolve uma promoção interna (banner/campanha). Dispara:
 *  - `view_promotion` quando ELA fica de fato visível (≥ 50%, uma vez);
 *  - `select_promotion` no clique.
 * Não altera layout — renderiza um `<div>` transparente ao redor do conteúdo.
 */
export function TrackedPromotion({
  promo,
  className,
  children,
}: {
  promo: TrackPromotion;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const viewed = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || viewed.current) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && e.intersectionRatio >= 0.5 && !viewed.current) {
            viewed.current = true;
            trackPromotion('view', promo);
            io.disconnect();
          }
        }
      },
      { threshold: [0.5] },
    );
    io.observe(el);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promo.promotion_id, promo.creative_slot]);

  return (
    <div ref={ref} className={className} onClickCapture={() => trackPromotion('select', promo)}>
      {children}
    </div>
  );
}
