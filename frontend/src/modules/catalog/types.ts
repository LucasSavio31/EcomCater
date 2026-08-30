/** Tipos do catálogo — espelham os DTOs de `api/app/modules/products` e `categories`. */

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  brand: string | null;
  price_cents: number;
  compare_at_price_cents: number | null;
  discount_pct: number | null;
  installments_max: number | null;
  in_stock: boolean;
  is_featured: boolean;
  primary_image_url: string | null;
  hover_image_url: string | null;
  rating_avg: number;
  rating_count: number;
}

export interface PriceFacet {
  min: number;
  max: number;
}

export interface SizeFacet {
  value: string;
  count: number;
}

export interface ProductFacets {
  price: PriceFacet;
  sizes: SizeFacet[];
}

export interface PagedProducts {
  items: ProductListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  facets: ProductFacets;
}

export type ProductSort = 'relevancia' | 'menor-preco' | 'maior-preco' | 'lancamentos';

export interface CategoryNode {
  id: string;
  name: string;
  slug: string;
  path: string;
  position: number;
  is_active: boolean;
  product_count: number;
  children: CategoryNode[];
}

export interface CategoryDetail {
  id: string;
  name: string;
  slug: string;
  path: string;
  parent_id: string | null;
  description: string | null;
  image_url: string | null;
  position: number;
  is_active: boolean;
  seo_title: string | null;
  seo_description: string | null;
}

export interface OptionValue {
  id: string;
  value: string;
  position: number;
  slug: string | null;
  image_id: string | null;
  swatch_thumb_url: string | null;
  swatch_medium_url: string | null;
}

export interface OptionType {
  id: string;
  name: string;
  is_size: boolean;
  is_color: boolean;
  position: number;
  values: OptionValue[];
}

export interface ProductVariant {
  id: string;
  sku: string;
  option_value_ids: string[];
  option_labels: string[];
  price_cents: number;
  compare_at_price_cents: number | null;
  /** null = estoque ilimitado */
  stock_qty: number | null;
  in_stock: boolean;
  weight_grams: number | null;
  is_active: boolean;
  position: number;
}

export interface ProductImage {
  id: string;
  alt: string | null;
  position: number;
  is_primary: boolean;
  variant_id: string | null;
  thumb_url: string;
  medium_url: string;
  zoom_url: string;
}

export interface ColorSibling {
  id: string;
  slug: string;
  name: string;
  color_name: string;
  image_url: string | null;
  is_current: boolean;
}

export interface ProductSpec {
  id: string;
  group: string | null;
  label: string;
  value: string;
  position: number;
}

export interface ProductReview {
  id: string;
  author_name: string;
  rating: number;
  title: string | null;
  body: string | null;
  status: string;
  created_at: string | null;
}

export interface BreadcrumbLink {
  name: string;
  url: string;
}

export interface ProductDetail {
  id: string;
  name: string;
  slug: string;
  sku_root: string | null;
  short_description: string | null;
  description: string | null;
  brand: string | null;
  category: { id: string; name: string; slug: string; path: string } | null;
  breadcrumb: BreadcrumbLink[];
  status: string;
  is_featured: boolean;
  price_cents: number;
  compare_at_price_cents: number | null;
  discount_pct: number | null;
  pix_discount_pct: number | null;
  installments_max: number | null;
  weight_grams: number;
  dimensions_mm: { length?: number; width?: number; height?: number };
  rating_avg: number;
  rating_count: number;
  seo_title: string | null;
  seo_description: string | null;
  color_name: string | null;
  color_siblings: ColorSibling[];
  option_types: OptionType[];
  variants: ProductVariant[];
  images: ProductImage[];
  specs: ProductSpec[];
  related: ProductListItem[];
  reviews: ProductReview[];
}

export interface SearchResultItem {
  type: 'product' | 'category';
  id: string;
  name: string;
  slug: string;
  url: string;
  price_cents: number | null;
  image_url: string | null;
}

export interface ProductQuery {
  category?: string;
  price_min?: number;
  price_max?: number;
  sizes?: string[];
  sort?: ProductSort;
  page?: number;
  page_size?: number;
}
