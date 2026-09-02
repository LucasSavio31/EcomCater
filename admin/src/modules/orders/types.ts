export type OrderStatus =
  | 'pending_payment'
  | 'paid'
  | 'processing'
  | 'tracking_available'
  | 'shipped'
  | 'delivered'
  | 'canceled'
  | 'refunded';

export interface OrderListItem {
  id: string;
  number: string;
  status: OrderStatus;
  payment_status: string;
  fulfillment_status: string;
  email: string;
  customer_name: string;
  grand_total_cents: number;
  placed_at: string | null;
  created_at: string;
  items_summary: string;
  items_count: number;
  suppliers: string[];
  /**
   * Etiqueta Melhor Envio:
   *  - 'ready'     = tem código de rastreio, liberada p/ imprimir
   *  - 'waiting'   = PDF pronto, aguardando o rastreio do ME
   *  - 'purchased' = enviada ao ME, gerando o PDF
   *  - 'none'      = sem etiqueta
   */
  me_label?: 'ready' | 'waiting' | 'purchased' | 'no_balance' | 'none';
}

export interface OrderPayment {
  provider: string;
  method: string;
  status: string;
  amount_cents: number;
  installments: number | null;
  provider_charge_id: string | null;
  paid_at: string | null;
  boleto_url: string | null;
  pix_qr_code: string | null;
}

export interface OrderItem {
  id?: string;
  sku: string;
  name: string;
  product_id: string | null;
  variant_label: string | null;
  cor: string | null;
  numero: string | null;
  cor_options: string[];
  numero_options: string[];
  supplier: string | null;
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
  phone?: string;
}

export interface ShippingServiceInfo {
  id?: string | number;
  service_id?: string | number;
  service?: string;
  carrier?: string;
  price_cents?: number;
  delivery_days?: number;
  /** Melhor Envio (etiqueta) */
  shipment_id?: string;
  protocol?: string;
  tracking_code?: string;
  label_url?: string;
  me_status?: string;
  me_reminder?: string;
}

export interface OrderDetail {
  number: string;
  status: OrderStatus;
  payment_status: string;
  fulfillment_status: string;
  email: string;
  customer_name: string;
  cpf: string | null;
  items: OrderItem[];
  items_total_cents: number;
  discount_cents: number;
  shipping_cents: number;
  grand_total_cents: number;
  coupon_code: string | null;
  shipping_method: string | null;
  shipping_service: ShippingServiceInfo | null;
  shipping_address: OrderAddress | null;
  customer_note: string | null;
  placed_at: string;
  events: OrderEvent[];
  payment?: OrderPayment | null;
  /** PNG (data URI) do QR com o número do pedido — só no GET individual. */
  qr_data_uri?: string;
}

/** Transições válidas por status atual (espelha o backend). */
export const ORDER_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending_payment: ['paid', 'canceled'],
  paid: ['processing', 'tracking_available', 'canceled', 'refunded'],
  processing: ['tracking_available', 'shipped', 'canceled', 'refunded'],
  tracking_available: ['shipped', 'delivered', 'canceled', 'refunded'],
  shipped: ['delivered', 'refunded'],
  delivered: ['refunded'],
  canceled: [],
  refunded: [],
};
