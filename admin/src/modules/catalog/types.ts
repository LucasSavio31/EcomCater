/** DTOs do catálogo (categorias + produtos) — espelham os routers admin da API. */

export interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  path?: string | null;
  description: string | null;
  position: number;
  is_active: boolean;
  image_url?: string | null;
  seo_title: string | null;
  seo_description: string | null;
  product_count?: number;
  children_count?: number;
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

export interface CategoryInput {
  name: string;
  parent_id?: string | null;
  description?: string | null;
  position?: number;
  is_active?: boolean;
  seo_title?: string | null;
  seo_description?: string | null;
}

export type ProductStatus = 'draft' | 'active' | 'archived';

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  status: ProductStatus;
  price_cents: number;
  compare_at_price_cents: number | null;
  in_stock: boolean;
  is_featured: boolean;
  primary_image_url: string | null;
  category_id: string | null;
  updated_at?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface OptionValue {
  id?: string;
  value: string;
  position?: number;
  slug?: string | null;
  image_id?: string | null;
  swatch_thumb_url?: string | null;
  swatch_medium_url?: string | null;
}

export interface OptionType {
  id?: string;
  name: string;
  is_size: boolean;
  is_color?: boolean;
  position?: number;
  values: OptionValue[];
}

export interface Variant {
  id: string;
  sku: string;
  option_value_ids: string[];
  option_labels?: string[];
  price_cents: number | null;
  compare_at_price_cents: number | null;
  /** null = estoque ilimitado */
  stock_qty: number | null;
  weight_grams: number | null;
  barcode: string | null;
  is_active: boolean;
  position: number;
}

export interface VariantInput {
  sku: string;
  option_value_ids: string[];
  price_cents?: number | null;
  compare_at_price_cents?: number | null;
  /** null = estoque ilimitado */
  stock_qty: number | null;
  weight_grams?: number | null;
  barcode?: string | null;
  is_active: boolean;
  position: number;
}

export interface ProductImage {
  id: string;
  url: string;
  medium_url?: string | null;
  thumb_url?: string | null;
  alt: string | null;
  position: number;
  is_primary: boolean;
  variant_id: string | null;
}

export interface ProductSpec {
  id?: string;
  group: string | null;
  label: string;
  value: string;
  position?: number;
}

export interface ProductReview {
  id: string;
  author_name: string;
  rating: number;
  title: string | null;
  body: string | null;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

export interface AdminReview extends ProductReview {
  product_id: string;
  product_name: string;
  product_slug: string | null;
}

export interface RelatedProduct {
  id: string;
  name: string;
  primary_image_url: string | null;
}

export interface ProductDetail {
  id: string;
  name: string;
  slug: string;
  status: ProductStatus;
  category_id: string | null;
  extra_category_ids: string[];
  brand: string | null;
  supplier?: string | null;
  short_description: string | null;
  description: string | null;
  price_cents: number;
  compare_at_price_cents: number | null;
  pix_discount_pct: number | null;
  installments_max: number | null;
  weight_grams: number;
  length_mm: number;
  width_mm: number;
  height_mm: number;
  is_featured: boolean;
  seo_title: string | null;
  seo_description: string | null;
  color_name: string | null;
  color_siblings: ColorSibling[];
  option_types: OptionType[];
  variants: Variant[];
  images: ProductImage[];
  specs: ProductSpec[];
  related_product_ids: string[];
  related_products?: RelatedProduct[];
}

export interface ColorSibling {
  id: string;
  slug: string;
  name: string;
  color_name: string;
  image_url: string | null;
  is_current: boolean;
}

export interface ProductInput {
  name: string;
  category_id?: string | null;
  extra_category_ids?: string[];
  status: ProductStatus;
  price_cents: number;
  compare_at_price_cents?: number | null;
  pix_discount_pct?: number | null;
  installments_max?: number | null;
  brand?: string | null;
  supplier?: string | null;
  short_description?: string | null;
  description?: string | null;
  weight_grams: number;
  length_mm: number;
  width_mm: number;
  height_mm: number;
  is_featured?: boolean;
  seo_title?: string | null;
  seo_description?: string | null;
  related_product_ids?: string[];
}
