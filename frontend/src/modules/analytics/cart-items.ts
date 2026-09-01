/**
 * Normalizadores de produto → `TrackItem` (formato canônico do tracker).
 * ESTA é a única origem de objetos de item para os eventos de e-commerce —
 * nenhuma página monta `{ id, name, price }` na mão.
 *
 * `item_id` (regra, alinhada ao feed do Merchant Center):
 *   SKU da variante  →  senão `sku_root` (item_group_id)  →  senão `slug`.
 */
import type { CartItem } from '@/modules/cart/types';
import type { OrderItem } from '@/modules/checkout/types';
import type {
  ProductDetail,
  ProductListItem,
  ProductVariant,
  SearchResultItem,
} from '@/modules/catalog/types';
import type { TrackItem } from './types';

/** Contexto de lista de origem — preservado view_item_list → select_item → view_item. */
export interface ListContext {
  id?: string;
  name?: string;
}

interface ItemOpts {
  index?: number;
  quantity?: number;
  list?: ListContext;
  coupon?: string;
  /** desconto monetário UNITÁRIO em reais (só se houver desconto comercial real) */
  discount?: number;
}

const reais = (cents: number | null | undefined) => Math.round((cents ?? 0)) / 100;

function withList(item: TrackItem, opts: ItemOpts): TrackItem {
  return {
    ...item,
    index: opts.index,
    quantity: opts.quantity ?? item.quantity,
    item_list_id: opts.list?.id,
    item_list_name: opts.list?.name,
    coupon: opts.coupon,
    discount: opts.discount,
  };
}

/** PDP: view_item, add_to_cart, add_to_wishlist. Passe a variante escolhida se houver. */
export function itemFromDetail(
  p: ProductDetail,
  opts: ItemOpts & { variant?: ProductVariant | null } = {},
): TrackItem {
  const v = opts.variant ?? null;
  return withList(
    {
      id: v?.sku || p.sku_root || p.slug,
      name: p.name,
      price: reais(v?.price_cents ?? p.price_cents),
      brand: p.brand ?? undefined,
      category: p.category?.name ?? undefined,
      categoryPath: p.category?.path ?? undefined,
      variant: v?.option_labels?.join(' / ') || undefined,
    },
    opts,
  );
}

/** Listas (categoria, vitrine, relacionados): view_item_list, select_item. */
export function itemFromListItem(p: ProductListItem, opts: ItemOpts = {}): TrackItem {
  return withList(
    {
      id: p.sku_root || p.slug,
      name: p.name,
      price: reais(p.price_cents),
      brand: p.brand ?? undefined,
    },
    opts,
  );
}

/** Resultados de busca (shape próprio da API de busca). */
export function itemFromSearchResult(p: SearchResultItem, opts: ItemOpts = {}): TrackItem {
  return withList(
    {
      id: p.sku_root || p.slug || p.id,
      name: p.name,
      price: reais(p.price_cents ?? 0),
      brand: p.brand ?? undefined,
    },
    opts,
  );
}

/** Itens do carrinho: view_cart, remove_from_cart, add_to_cart (stepper), begin_checkout, add_shipping/payment_info. */
export function cartToTrackItems(items: CartItem[], opts: ItemOpts = {}): TrackItem[] {
  return items.map((i, idx) =>
    withList(
      {
        id: i.sku || i.variant_id,
        name: i.product_name,
        price: reais(i.unit_price_cents),
        quantity: i.quantity,
        variant: i.variant_label ?? undefined,
      },
      { ...opts, index: opts.index ?? idx },
    ),
  );
}

/** Itens do pedido: purchase, refund. */
export function orderToTrackItems(items: OrderItem[]): TrackItem[] {
  return items.map((i, idx) => ({
    id: i.sku,
    name: i.name,
    price: reais(i.unit_price_cents),
    quantity: i.quantity,
    variant: i.variant_label ?? undefined,
    index: idx,
  }));
}
