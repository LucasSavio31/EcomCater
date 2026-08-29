import type { Metadata } from 'next';
import { getBanners } from '@/modules/banners/api';
import { getFeaturedProducts, getCategoryTree, getProducts } from '@/modules/catalog/api';
import { getTheme } from '@/modules/theme';
import { BannerGrid } from '@/components/layout/banner-grid';
import { HeroBanner } from '@/components/layout/hero-banner';
import { ProductGrid } from '@/components/catalog/product-grid';
import { SizeShortcuts, type SizeShortcut } from '@/components/catalog/size-shortcuts';
import { NewsletterForm } from '@/components/layout/newsletter-form';
import { buildMetadata } from '@/lib/seo';

export const dynamic = 'force-dynamic';

export function generateMetadata(): Metadata {
  return buildMetadata({
    description: 'Novidades, ofertas e os produtos mais buscados da loja.',
    path: '/',
  });
}

async function homeSizeShortcuts(): Promise<SizeShortcut[]> {
  const tree = await getCategoryTree();
  const root = tree.find((c) => c.product_count > 0) ?? tree[0];
  if (!root) return [];
  const page = await getProducts({ category: root.path, page_size: 1 });
  return page.facets.sizes
    .filter((s) => s.count > 0)
    .slice(0, 12)
    .map((s) => ({ label: s.value, url: `/categoria/${root.path}?size=${encodeURIComponent(s.value)}` }));
}

export default async function HomePage() {
  const [hero, showcase, featured, shortcuts, theme] = await Promise.all([
    getBanners('hero'),
    getBanners('showcase'),
    getFeaturedProducts(12),
    homeSizeShortcuts(),
    getTheme(),
  ]);

  const showHero = theme.hero_enabled && hero.length > 0;
  const nothing = hero.length === 0 && showcase.length === 0 && featured.length === 0;

  return (
    <div className="flex flex-col gap-10">
      {showHero && (
        <HeroBanner
          banners={hero}
          mode={theme.hero_mode}
          autoplaySeconds={theme.hero_autoplay_seconds}
        />
      )}

      <SizeShortcuts shortcuts={shortcuts} heading="Compre por numeração" />

      {featured.length > 0 && (
        <section aria-labelledby="vitrine-title" className="flex flex-col gap-4">
          <h2 id="vitrine-title" className="text-lg font-semibold sm:text-xl">
            Mais buscados
          </h2>
          <ProductGrid products={featured} priorityCount={4} />
        </section>
      )}

      {showcase.length > 0 && (
        <section aria-label="Coleções">
          <BannerGrid banners={showcase.slice(0, 4)} variant="showcase" />
        </section>
      )}

      {nothing && (
        <section className="rounded-card border border-dashed border-surface-border p-10 text-center">
          <h1 className="text-xl font-semibold">Loja no ar</h1>
          <p className="mt-1 text-sm text-text-muted">
            O catálogo aparece aqui assim que houver produtos e banners cadastrados.
          </p>
        </section>
      )}

      <section
        aria-labelledby="newsletter-home-title"
        className="rounded-card border border-surface-border bg-bg-subtle p-6"
      >
        <h2 id="newsletter-home-title" className="text-lg font-semibold">
          Fique por dentro
        </h2>
        <p className="mb-3 text-sm text-text-muted">
          Cadastre seu e-mail e receba novidades e ofertas em primeira mão.
        </p>
        <NewsletterForm />
      </section>
    </div>
  );
}
