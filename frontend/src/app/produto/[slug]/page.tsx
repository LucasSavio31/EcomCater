import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Accordion } from '@ecom/ui';
import { getProduct } from '@/modules/catalog/api';
import { getTheme } from '@/modules/theme';
import { resolveMediaUrl } from '@/lib/media';
import { Breadcrumbs, type Crumb } from '@/components/catalog/breadcrumbs';
import { Stars } from '@/components/catalog/stars';
import { ProductCarousel } from '@/components/catalog/product-carousel';
import { PdpMain } from '@/components/pdp/pdp-main';
import { ReviewForm } from '@/components/pdp/review-form';
import { FreeShippingProgress } from '@/components/layout/free-shipping-progress';
import { TrackOnMount } from '@/components/analytics/track-on-mount';
import { itemFromDetail, itemFromListItem } from '@/modules/analytics';
import {
  breadcrumbJsonLd,
  buildMetadata,
  jsonLdScript,
  productJsonLd,
  SITE_URL,
} from '@/lib/seo';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return buildMetadata({ title: 'Produto', path: `/produto/${slug}`, noindex: true });

  const image = product.images.find((i) => i.is_primary) ?? product.images[0];
  const imageUrl = image ? resolveMediaUrl(image.zoom_url) : null;
  return buildMetadata({
    title: product.seo_title || product.name,
    description:
      product.seo_description ||
      product.short_description ||
      `${product.name} — compre com segurança na nossa loja.`,
    path: `/produto/${product.slug}`,
    images: imageUrl ? [imageUrl] : undefined,
  });
}

function buildCrumbs(items: { name: string; url: string }[]): Crumb[] {
  return [{ name: 'Início', url: '/' }, ...items.map((c) => ({ name: c.name, url: c.url }))];
}

export default async function ProdutoPage({ params }: PageProps) {
  const { slug } = await params;
  const [product, theme] = await Promise.all([getProduct(slug), getTheme()]);

  if (!product) notFound();

  const crumbs = buildCrumbs(product.breadcrumb ?? []);
  const primaryImage = product.images.find((i) => i.is_primary) ?? product.images[0];
  const primaryImageUrl = primaryImage ? resolveMediaUrl(primaryImage.zoom_url) : null;
  const inStock = product.variants.length === 0 || product.variants.some((v) => v.in_stock);

  const specGroups = new Map<string, typeof product.specs>();
  for (const spec of product.specs) {
    const key = spec.group ?? 'Especificações';
    const list = specGroups.get(key) ?? [];
    list.push(spec);
    specGroups.set(key, list);
  }

  const accordionItems = [
    ...(product.description
      ? [
          {
            id: 'descricao',
            title: 'Sobre o produto',
            content: (
              <div
                className="max-w-none text-sm leading-relaxed text-text-muted [&_a]:text-primary [&_a]:underline [&_h2]:mb-1.5 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-text [&_h3]:mb-1 [&_h3]:mt-2.5 [&_h3]:font-semibold [&_h3]:text-text [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
                // HTML vindo do admin (conteúdo controlado internamente).
                dangerouslySetInnerHTML={{ __html: product.description }}
              />
            ),
          },
        ]
      : []),
    ...(product.specs.length > 0
      ? [
          {
            id: 'specs',
            title: 'Especificações',
            content: (
              <div className="flex flex-col gap-4">
                {[...specGroups.entries()].map(([group, specs]) => (
                  <div key={group}>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text">
                      {group}
                    </p>
                    <dl className="divide-y divide-surface-border text-sm">
                      {specs.map((spec) => (
                        <div key={spec.id} className="flex justify-between gap-4 py-1.5">
                          <dt className="text-text-muted">{spec.label}</dt>
                          <dd className="text-right text-text">{spec.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ))}
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="flex flex-col gap-8">
      <TrackOnMount event="view_item" dedupeKey={product.slug} items={[itemFromDetail(product)]} />
      {product.related.length > 0 && (
        <TrackOnMount
          event="view_item_list"
          dedupeKey={`related:${product.slug}`}
          itemListId="related_products"
          itemListName="Produtos relacionados"
          items={product.related
            .slice(0, 20)
            .map((p, i) =>
              itemFromListItem(p, {
                index: i,
                list: { id: 'related_products', name: 'Produtos relacionados' },
              }),
            )}
        />
      )}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLdScript([
            productJsonLd({
              name: product.name,
              description: product.short_description ?? undefined,
              sku: product.sku_root ?? undefined,
              brand: product.brand ?? undefined,
              images: primaryImageUrl ? [primaryImageUrl] : undefined,
              priceCents: product.price_cents,
              availability: inStock ? 'InStock' : 'OutOfStock',
              url: `${SITE_URL}/produto/${product.slug}`,
              ratingValue: product.rating_count > 0 ? product.rating_avg : undefined,
              ratingCount: product.rating_count > 0 ? product.rating_count : undefined,
            }),
            breadcrumbJsonLd(crumbs.map((c) => ({ name: c.name, path: c.url ?? '/' }))),
          ]),
        }}
      />

      {/* Barra de frete grátis fixa no topo — só aparece com item no carrinho */}
      <FreeShippingProgress
        sticky
        variant="bar"
        className="mx-auto max-w-6xl text-center text-text-muted"
      />

      <Breadcrumbs items={crumbs} />

      <PdpMain
        product={product}
        redirectAfterAdd={theme.cart_redirect_after_add}
        miniCart={theme.mini_cart_enabled}
        theme={theme}
      />

      {accordionItems.length > 0 && (
        <section aria-label="Detalhes do produto">
          <Accordion items={accordionItems} multiple defaultOpen={['descricao']} />
        </section>
      )}

      <section aria-labelledby="reviews-title" className="flex flex-col gap-4">
        <h2 id="reviews-title" className="text-lg font-semibold">
          Avaliações {product.rating_count > 0 && `(${product.rating_count})`}
        </h2>

        {product.reviews.length > 0 ? (
          <ul className="flex flex-col divide-y divide-surface-border">
            {product.reviews.map((review) => (
              <li key={review.id} className="flex flex-col gap-1 py-3">
                <div className="flex items-center gap-2">
                  <Stars value={review.rating} count={undefined} hideCount />
                  <span className="text-sm font-medium">{review.author_name}</span>
                </div>
                {review.title && <p className="text-sm font-medium">{review.title}</p>}
                {review.body && <p className="text-sm text-text-muted">{review.body}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">Este produto ainda não tem avaliações.</p>
        )}

        <div className="rounded-card border border-surface-border p-4">
          <p className="mb-3 text-sm font-semibold">Avalie este produto</p>
          <ReviewForm slug={product.slug} />
        </div>
      </section>

      {/* Relacionados: sempre no fim da página, acima do rodapé (se ligado no admin) */}
      {theme.pdp_related_enabled && product.related.length > 0 && (
        <section aria-labelledby="related-title" className="flex flex-col gap-4">
          <h2 id="related-title" className="text-lg font-semibold">
            Você também pode gostar
          </h2>
          <ProductCarousel
            products={product.related}
            ariaLabel="Produtos relacionados"
            listId="related_products"
            listName="Produtos relacionados"
          />
        </section>
      )}
    </div>
  );
}
