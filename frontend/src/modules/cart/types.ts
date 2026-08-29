/** DTOs do carrinho — espelham `CartOut` do backend (`GET /api/cart`). */

export interface CartItem {
  id: string;
  product_id: string;
  variant_id: string;
  product_name: string;
  product_slug: string;
  variant_label: string | null;
  sku: string;
  image_url: string | null;
  unit_price_cents: number;
  quantity: number;
  line_total_cents: number;
  in_stock: boolean;
  max_qty: number;
  price_changed: boolean;
}

export interface CartTotals {
  items_count: number;
  items_total_cents: number;
  discount_cents: number;
  shipping_cents: number;
  grand_total_cents: number;
  free_shipping_threshold_cents: number | null;
  free_shipping_remaining_cents: number | null;
}

export interface ShippingOption {
  id: string;
  service: string;
  carrier: string;
  price_cents: number;
  delivery_days: number;
  provider?: string;
}

export interface Cart {
  token: string;
  items: CartItem[];
  totals: CartTotals;
  coupon_code: string | null;
  coupon_error: string | null;
  shipping_zip: string | null;
  selected_shipping: ShippingOption | null;
}

export const EMPTY_CART: Cart = {
  token: '',
  items: [],
  totals: {
    items_count: 0,
    items_total_cents: 0,
    discount_cents: 0,
    shipping_cents: 0,
    grand_total_cents: 0,
    free_shipping_threshold_cents: null,
    free_shipping_remaining_cents: null,
  },
  coupon_code: null,
  coupon_error: null,
  shipping_zip: null,
  selected_shipping: null,
};
