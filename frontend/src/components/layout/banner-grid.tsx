import Link from 'next/link';
import Image from 'next/image';
import type { Banner } from '@/modules/banners/types';
import { resolveMediaUrl } from '@/lib/media';
import { TrackedPromotion } from '@/components/analytics/tracked-promotion';

interface BannerGridProps {
  banners: Banner[];
  /** `hero` = destaque grande; `showcase` = faixas menores. */
  variant?: 'hero' | 'showcase';
  priority?: boolean;
}

/** Grade de banners clicáveis com imagem responsiva (mobile/desktop). */
export function BannerGrid({ banners, variant = 'hero', priority = false }: BannerGridProps) {
  if (banners.length === 0) return null;

  const cols =
    banners.length === 1
      ? 'grid-cols-1'
      : banners.length === 2
        ? 'grid-cols-1 sm:grid-cols-2'
        : banners.length === 3
          ? 'grid-cols-1 sm:grid-cols-3'
          : 'grid-cols-2 lg:grid-cols-4';

  const aspect = variant === 'hero' ? 'aspect-[16/10] sm:aspect-[21/9]' : 'aspect-[4/3] sm:aspect-[3/2]';

  return (
    <ul className={`grid gap-3 ${cols}`}>
      {banners.map((banner, i) => {
        const src = resolveMediaUrl(banner.image_url ?? banner.image_desktop_url);
        const alt = banner.alt ?? banner.title ?? 'Banner promocional';
        const inner = (
          <span className={`relative block w-full overflow-hidden rounded-card bg-bg-subtle ${aspect}`}>
            {src && (
              <Image
                src={src}
                alt={alt}
                fill
                sizes="(min-width: 640px) 100vw, 100vw"
                priority={priority && i === 0}
                unoptimized={/\.gif($|\?)/i.test(src)}
                className="object-cover"
              />
            )}
          </span>
        );

        return (
          <li key={banner.id}>
            <TrackedPromotion
              promo={{
                promotion_id: banner.id,
                promotion_name: banner.title ?? undefined,
                creative_name: banner.title ?? `${banner.slot}-${i + 1}`,
                creative_slot: banner.slot,
              }}
            >
              {banner.link_url ? (
                <Link href={banner.link_url} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
                  {inner}
                </Link>
              ) : (
                inner
              )}
            </TrackedPromotion>
          </li>
        );
      })}
    </ul>
  );
}
