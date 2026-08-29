export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'canceled'
  | 'refunded';

export interface OrderListItem {
  id: string;
  number: string;
  status: OrderStatus;
  payment_status: string;
  email: string;
  grand_total_cents: number;
  placed_at: string;
}

export interface OrderItem {
  sku: string;
  name: string;
  variant_label: string | null;
  image_url: string | null;
  unit_price_cents: number;
  quantity: number;
  total_cents: number;
}

export interface OrderEvent {
  type: string;
  from_status: string | null;
  to_status: string | null;
  message: string | null;
  actor_type: 'system' | 'admin' | 'customer';
  created_at: string;
}

export interface OrderAddress {
  recipient_name?: string;
  zip?: string;
  street?: string;
  number?: string;
  complement?: string;
  district?: string;
  city?: string;
  state?: string;
}

export interface OrderDetail {
  number: string;
  status: OrderStatus;
  payment_status: string;
  fulfillment_status: string;
  email: string;
  items: OrderItem[];
  items_total_cents: number;
  discount_cents: number;
  shipping_cents: number;
  grand_total_cents: number;
  coupon_code: string | null;
  shipping_method: string | null;
  shipping_service: string | null;
  shipping_address: OrderAddress | null;
  customer_note: string | null;
  placed_at: string;
  events: OrderEvent[];
}

/** Transições válidas por status atual (espelha o backend). */
export const ORDER_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending_payment: ['paid', 'canceled'],
  paid: ['processing', 'canceled', 'refunded'],
  processing: ['shipped', 'canceled', 'refunded'],
  shipped: ['delivered', 'refunded'],
  delivered: ['refunded'],
  canceled: [],
  refunded: [],
};
