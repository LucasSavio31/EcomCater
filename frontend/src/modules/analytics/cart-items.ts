import type { CartItem } from '@/modules/cart/types';
import type { OrderItem } from '@/modules/checkout/types';
import type { TrackItem } from './types';

export function cartToTrackItems(items: CartItem[]): TrackItem[] {
  return items.map((i) => ({
    id: i.sku || i.variant_id,
    name: i.product_name,
    price: i.unit_price_cents / 100,
    quantity: i.quantity,
    variant: i.variant_label ?? undefined,
  }));
}

export function orderToTrackItems(items: OrderItem[]): TrackItem[] {
  return items.map((i) => ({
    id: i.sku,
    name: i.name,
    price: i.unit_price_cents / 100,
    quantity: i.quantity,
    variant: i.variant_label ?? undefined,
  }));
}
