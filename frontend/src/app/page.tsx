import type { Metadata } from 'next';
import { getBanners } from '@/modules/banners/api';
import { getHomeSections, getCategoryTree, getProducts } from '@/modules/catalog/api';
import type { ProductListItem } from '@/modules/catalog/types';
import { getTheme } from '@/modules/theme';
import { BannerGrid } from '@/components/layout/banner-grid';
import { HeroBanner } from '@/components/layout/hero-banner';
import { ProductGrid } from '@/components/catalog/product-grid';
import { SizeShortcuts, type SizeShortcut } from '@/components/catalog/size-shortcuts';
import { NewsletterForm } from '@/components/layout/newsletter-form';
import { TrackOnMount } from '@/components/analytics/track-on-mount';
import { itemFromListItem } from '@/modules/analytics';
import { buildMetadata } from '@/lib/seo';

export const revalidate = 120; // ISR — invalidação por tag no /api/revalidate

export async function generateMetadata(): Promise<Metadata> {
  const theme = await getTheme();
  return buildMetadata({
    description: 'Novidades, ofertas e os produtos mais buscados da loja.',
    path: '/',
    siteName: theme.store_name,
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

async function homeFilterSummary() {
  const tree = await getCategoryTree();
  const root = tree.find((c) => c.product_count > 0) ?? tree[0];
  const categories = tree.slice(0, 8).map((c) => ({ name: c.name, path: c.path }));
  const priceLinks = root
    ? [
        { label: 'Até R$ 300', url: `/categoria/${root.path}?price_max=30000` },
        { label: 'R$ 300–600', url: `/categoria/${root.path}?price_min=30000&price_max=60000` },
        { label: 'Acima de R$ 600', url: `/categoria/${root.path}?price_min=60000` },
      ]
    : [];
  return { categories, priceLinks };
}

function HomeProductSection({
  id,
  title,
  products,
  theme,
  priorityCount = 0,
}: {
  id: string;
  title: string;
  products: ProductListItem[];
  theme: Awaited<ReturnType<typeof getTheme>>;
  priorityCount?: number;
}) {
  if (products.length === 0) return null;
  return (
    <section aria-labelledby={`${id}-title`} className="flex flex-col gap-4">
      <TrackOnMount
        event="view_item_list"
        dedupeKey={id}
        itemListId={id}
        itemListName={title}
        items={products
          .slice(0, 20)
          .map((p, i) => itemFromListItem(p, { index: i, list: { id, name: title } }))}
      />
      <h2 id={`${id}-title`} className="text-lg font-semibold sm:text-xl">
        {title}
      </h2>
      <ProductGrid
        products={products}
        priorityCount={priorityCount}
        listId={id}
        listName={title}
        buyButtonLabel={theme.card_buy_button_enabled ? theme.card_buy_button_label : undefined}
      />
    </section>
  );
}

export default async function HomePage() {
  const [hero, showcase, sections, shortcuts, theme, filterSummary] = await Promise.all([
    getBanners('hero'),
    getBanners('showcase'),
    getHomeSections(),
    homeSizeShortcuts(),
    getTheme(),
    homeFilterSummary(),
  ]);

  const showHero = theme.hero_enabled && hero.length > 0;
  const showFilterSummary =
    theme.filters_on_home &&
    ((theme.filter_category_enabled && filterSummary.categories.length > 0) ||
      (theme.filter_price_enabled && filterSummary.priceLinks.length > 0));
  const anySection =
    sections.mais_buscados.length + sections.tenis.length + sections.feminino.length > 0;
  const nothing = hero.length === 0 && showcase.length === 0 && !anySection;

  return (
    <div className="flex flex-col gap-10">
      {showHero && (
        <>
          <div className="hidden sm:block">
            <HeroBanner
              banners={hero}
              viewport="desktop"
              mode={theme.hero_mode}
              autoplaySeconds={theme.hero_autoplay_seconds}
            />
          </div>
          <div className="sm:hidden">
            <HeroBanner
              banners={hero}
              viewport="mobile"
              mode={theme.hero_mode}
              autoplaySeconds={theme.hero_autoplay_seconds}
            />
          </div>
        </>
      )}

      {theme.filters_on_home && theme.filter_size_enabled && (
        <SizeShortcuts shortcuts={shortcuts} heading="Compre por numeração" />
      )}

      {showFilterSummary && (
        <section aria-label="Filtrar" className="flex flex-col gap-3">
          {theme.filter_category_enabled && filterSummary.categories.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">Categorias:</span>
              {filterSummary.categories.map((c) => (
                <a
                  key={c.path}
                  href={`/categoria/${c.path}`}
                  className="rounded-card border border-surface-border px-3 py-1 text-sm hover:border-primary"
                >
                  {c.name}
                </a>
              ))}
            </div>
          )}
          {theme.filter_price_enabled && filterSummary.priceLinks.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">Preço:</span>
              {filterSummary.priceLinks.map((p) => (
                <a
                  key={p.url}
                  href={p.url}
                  className="rounded-card border border-surface-border px-3 py-1 text-sm hover:border-primary"
                >
                  {p.label}
                </a>
              ))}
            </div>
          )}
        </section>
      )}

      <HomeProductSection
        id="home_featured"
        title="Mais buscados"
        products={sections.mais_buscados}
        theme={theme}
        priorityCount={4}
      />

      {showcase.length > 0 && (
        <section aria-label="Coleções">
          <BannerGrid banners={showcase.slice(0, 4)} variant="showcase" />
        </section>
      )}

      <HomeProductSection
        id="home_tenis"
        title="Tênis"
        products={sections.tenis}
        theme={theme}
      />

      <HomeProductSection
        id="home_feminino"
        title="Feminino"
        products={sections.feminino}
        theme={theme}
      />

      {nothing && (
        <section className="rounded-card border border-dashed border-surface-border p-10 text-center">
          <h1 className="text-xl font-semibold">Loja no ar</h1>
          <p className="mt-1 text-sm text-text-muted">
            O catálogo aparece aqui assim que houver produtos e banners cadastrados.
          </p>
        </section>
      )}

      {theme.newsletter_enabled && (
        <section
          aria-labelledby="newsletter-home-title"
          className="rounded-card border border-surface-border p-6"
          style={{ background: theme.newsletter_bg_color, color: theme.newsletter_text_color }}
        >
          <h2 id="newsletter-home-title" className="text-lg font-semibold">
            {theme.newsletter_title}
          </h2>
          <p className="mb-3 text-sm opacity-80">{theme.newsletter_subtitle}</p>
          <NewsletterForm
            buttonColor={theme.newsletter_button_color}
            buttonTextColor={theme.newsletter_button_text_color}
          />
        </section>
      )}
    </div>
  );
}
