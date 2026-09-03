'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { cartApi } from './api';
import { EMPTY_CART, type Cart } from './types';

/**
 * Contexto de carrinho — integração real com `/api/cart` (Fase 4).
 *
 * O carrinho de convidado vive no cookie httpOnly `cart_token`; o de cliente
 * logado, no `user_id`. As mutações devolvem o carrinho inteiro, então o estado
 * local é sempre o último `CartOut` recebido.
 */

interface CartState {
  cart: Cart;
  loading: boolean;
  /** Contagem de itens (badge do header). */
  count: number;
  /** Subtotal em centavos (barra de frete grátis). */
  subtotalCents: number;
  refresh: () => Promise<void>;
  addItem: (variantId: string, quantity?: number) => Promise<{ ok: boolean; error?: string }>;
  updateItem: (itemId: string, quantity: number) => Promise<{ ok: boolean }>;
  removeItem: (itemId: string) => Promise<{ ok: boolean }>;
  setZip: (zip: string) => Promise<void>;
  applyCoupon: (code: string) => Promise<void>;
  removeCoupon: () => Promise<void>;
  selectShipping: (serviceId: string) => Promise<void>;
  /** Mini-carrinho lateral. */
  miniCartOpen: boolean;
  openMiniCart: () => void;
  closeMiniCart: () => void;
}

const CartContext = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<Cart>(EMPTY_CART);
  const [loading, setLoading] = useState(true);
  const [miniCartOpen, setMiniCartOpen] = useState(false);
  const mounted = useRef(true);

  const openMiniCart = useCallback(() => setMiniCartOpen(true), []);
  const closeMiniCart = useCallback(() => setMiniCartOpen(false), []);

  const apply = useCallback((next: Cart) => {
    if (mounted.current) setCart(next);
  }, []);

  const refresh = useCallback(async () => {
    const res = await cartApi.get();
    if (res.ok) apply(res.data);
    if (mounted.current) setLoading(false);
  }, [apply]);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  // Sincroniza o carrinho ao VOLTAR PARA A ABA (não a cada `focus` de window —
  // no mobile o foco muda ao abrir/fechar o teclado, e o refetch + setCart a
  // cada tecla travava os campos do checkout). `visibilitychange` só dispara
  // numa troca real de aba/app.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refresh();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [refresh]);

  const addItem = useCallback<CartState['addItem']>(
    async (variantId, quantity = 1) => {
      const res = await cartApi.addItem(variantId, quantity);
      if (res.ok) {
        apply(res.data);
        return { ok: true };
      }
      return { ok: false, error: res.error.message };
    },
    [apply],
  );

  const updateItem = useCallback<CartState['updateItem']>(
    async (itemId, quantity) => {
      const res = await cartApi.updateItem(itemId, quantity);
      if (res.ok) apply(res.data);
      return { ok: res.ok };
    },
    [apply],
  );

  const removeItem = useCallback<CartState['removeItem']>(
    async (itemId) => {
      const res = await cartApi.removeItem(itemId);
      if (res.ok) apply(res.data);
      return { ok: res.ok };
    },
    [apply],
  );

  const setZip = useCallback<CartState['setZip']>(
    async (zip) => {
      const res = await cartApi.setZip(zip);
      if (res.ok) apply(res.data);
    },
    [apply],
  );

  const applyCoupon = useCallback<CartState['applyCoupon']>(
    async (code) => {
      const res = await cartApi.applyCoupon(code);
      if (res.ok) apply(res.data);
    },
    [apply],
  );

  const removeCoupon = useCallback<CartState['removeCoupon']>(async () => {
    const res = await cartApi.removeCoupon();
    if (res.ok) apply(res.data);
  }, [apply]);

  const selectShipping = useCallback<CartState['selectShipping']>(
    async (serviceId) => {
      const res = await cartApi.selectShipping(serviceId);
      if (res.ok) apply(res.data);
    },
    [apply],
  );

  const value = useMemo<CartState>(
    () => ({
      cart,
      loading,
      count: cart.totals.items_count,
      subtotalCents: cart.totals.items_total_cents,
      refresh,
      addItem,
      updateItem,
      removeItem,
      setZip,
      applyCoupon,
      removeCoupon,
      selectShipping,
      miniCartOpen,
      openMiniCart,
      closeMiniCart,
    }),
    [
      cart,
      loading,
      refresh,
      addItem,
      updateItem,
      removeItem,
      setZip,
      applyCoupon,
      removeCoupon,
      selectShipping,
      miniCartOpen,
      openMiniCart,
      closeMiniCart,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartState {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error('useCart precisa estar dentro de <CartProvider>.');
  }
  return ctx;
}
