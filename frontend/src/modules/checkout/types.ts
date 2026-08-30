/** DTOs do checkout — espelham `orders` e `payment` do backend. */

export interface PaymentMethods {
  credit_card: boolean;
  pix: boolean;
  boleto: boolean;
  max_installments: number;
}

export interface AddressPayload {
  recipient_name: string;
  zip: string;
  street: string;
  number: string;
  complement?: string | null;
  district: string;
  city: string;
  state: string;
  country?: string;
  phone?: string | null;
}

export interface CheckoutPayload {
  email: string;
  cpf?: string | null;
  shipping_address: AddressPayload;
  billing_address?: AddressPayload | null;
  customer_note?: string | null;
  shipping_service_id?: string | null;
  idempotency_key?: string | null;
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
  actor_type: string;
  created_at: string | null;
}

export interface OrderPayment {
  method: string;
  status: string;
  amount_cents: number;
  installments: number | null;
  paid_at: string | null;
  pix_qr_code: string | null;
  boleto_url: string | null;
}

export interface Order {
  id: string;
  number: string;
  status: string;
  payment_status: string;
  fulfillment_status: string;
  email: string;
  payment?: OrderPayment | null;
  items: OrderItem[];
  items_total_cents: number;
  discount_cents: number;
  shipping_cents: number;
  grand_total_cents: number;
  coupon_code: string | null;
  shipping_method: string | null;
  shipping_service: Record<string, unknown> | null;
  shipping_address: Record<string, string>;
  customer_note: string | null;
  placed_at: string | null;
  events: OrderEvent[];
}

export interface CardPayload {
  number: string;
  holder_name: string;
  exp_month: number;
  exp_year: number;
  cvv: string;
  installments: number;
}

export interface ChargePayload {
  order_number: string;
  method: 'credit_card' | 'pix' | 'boleto';
  card?: CardPayload | null;
}

export interface ChargeResult {
  payment_id: string;
  order_number: string;
  method: string;
  status: string;
  amount_cents: number;
  pix_qr_code: string | null;
  pix_expires_at: string | null;
  boleto_url: string | null;
  boleto_barcode: string | null;
}

export interface PaymentStatus {
  order_number: string;
  order_status: string;
  payment_status: string;
  method: string | null;
  updated_at: string | null;
}
