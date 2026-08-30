'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import type { Banner } from '@/modules/banners/types';
import { resolveMediaUrl } from '@/lib/media';

interface HeroBannerProps {
  banners: Banner[];
  mode: 'carousel' | 'static';
  autoplaySeconds: number;
}

/**
 * Banner principal da home, largura total (full-bleed) como na catlifestyle:
 * baixo e largo no desktop, mais alto no mobile.
 *  - `static`: mostra só o primeiro banner
 *  - `carousel`: setas, bullets, arrastar e autoplay opcional
 */
export function HeroBanner({ banners, mode, autoplaySeconds }: HeroBannerProps) {
  const slides = mode === 'static' ? banners.slice(0, 1) : banners.slice(0, 8);
  const [index, setIndex] = useState(0);
  const touchX = useRef<number | null>(null);
  const indexRef = useRef(0);
  const count = slides.length;

  const go = useCallback(
    (next: number) => {
      if (count > 0) setIndex(((next % count) + count) % count);
    },
    [count],
  );

  useEffect(() => {
    indexRef.current = index;
  }, [index]);

  useEffect(() => {
    if (mode !== 'carousel' || count < 2 || autoplaySeconds <= 0) return;
    const id = window.setInterval(() => go(indexRef.current + 1), autoplaySeconds * 1000);
    return () => window.clearInterval(id);
  }, [mode, count, autoplaySeconds, go]);

  if (count === 0) return null;

  return (
    <section
      aria-label="Destaques"
      aria-roledescription={mode === 'carousel' && count > 1 ? 'carrossel' : undefined}
      className="relative left-1/2 right-1/2 -mx-[50vw] w-screen max-w-[100vw] overflow-x-clip"
    >
      <div
        className="relative w-full"
        onTouchStart={(e) => {
          touchX.current = e.touches[0]?.clientX ?? null;
        }}
        onTouchEnd={(e) => {
          const end = e.changedTouches[0]?.clientX;
          if (touchX.current === null || end === undefined || mode !== 'carousel') return;
          const dx = end - touchX.current;
          if (Math.abs(dx) > 40) go(index + (dx < 0 ? 1 : -1));
          touchX.current = null;
        }}
      >
        <div className="flex transition-transform duration-500 ease-out" style={{ transform: `translateX(-${index * 100}%)` }}>
          {slides.map((banner, i) => {
            const src = resolveMediaUrl(banner.image_url ?? banner.image_desktop_url);
            const alt = banner.alt ?? banner.title ?? 'Banner promocional';
            const media = (
              <span className="relative block aspect-[4/5] w-full bg-bg-subtle sm:aspect-[2/1] lg:aspect-[64/21]">
                {src && (
                  <Image
                    src={src}
                    alt={alt}
                    fill
                    sizes="100vw"
                    priority={i === 0}
                    unoptimized={/\.gif($|\?)/i.test(src)}
                    className="object-cover"
                  />
                )}
              </span>
            );
            return (
              <div key={banner.id} className="w-full shrink-0" aria-hidden={i !== index}>
                {banner.link_url ? (
                  <Link href={banner.link_url} tabIndex={i === index ? 0 : -1} className="block">
                    {media}
                  </Link>
                ) : (
                  media
                )}
              </div>
            );
          })}
        </div>

        {mode === 'carousel' && count > 1 && (
          <>
            <button
              type="button"
              onClick={() => go(index - 1)}
              aria-label="Anterior"
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white backdrop-blur transition hover:bg-black/60 sm:left-4"
            >
              ‹
            </button>
            <button
              type="button"
              onClick={() => go(index + 1)}
              aria-label="Próximo"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white backdrop-blur transition hover:bg-black/60 sm:right-4"
            >
              ›
            </button>
            <div className="absolute inset-x-0 bottom-3 flex justify-center gap-2">
              {slides.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  aria-label={`Ir para o slide ${i + 1}`}
                  aria-current={i === index}
                  onClick={() => setIndex(i)}
                  className={`h-1.5 rounded-full transition-all ${
                    i === index ? 'w-6 bg-white' : 'w-1.5 bg-white/60'
                  }`}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
