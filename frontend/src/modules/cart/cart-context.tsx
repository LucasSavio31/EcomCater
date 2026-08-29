'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import type { ReactNode } from 'react';

/**
 * Contexto de carrinho — PLACEHOLDER da Fase 3.
 *
 * A Fase 4 substitui isto pela integração real com `POST /api/cart`. Por ora
 * mantemos só o que o header precisa: a contagem de itens (badge) e o subtotal
 * (barra de progresso do frete grátis), persistidos em `localStorage` para
 * sobreviver à navegação. `addItem` apenas incrementa — não fala com a API.
 */

const COUNT_KEY = 'ecom:cart:count';
const SUBTOTAL_KEY = 'ecom:cart:subtotal_cents';

interface CartState {
  count: number;
  subtotalCents: number;
  addItem: (input?: { priceCents?: number; quantity?: number }) => void;
  clear: () => void;
}

const CartContext = createContext<CartState | null>(null);

function readNumber(key: string): number {
  if (typeof window === 'undefined') return 0;
  const raw = window.localStorage.getItem(key);
  const value = raw ? Number.parseInt(raw, 10) : 0;
  return Number.isFinite(value) && value > 0 ? value : 0;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0);
  const [subtotalCents, setSubtotalCents] = useState(0);

  // Hidrata do localStorage só no cliente (evita divergência de SSR).
  useEffect(() => {
    setCount(readNumber(COUNT_KEY));
    setSubtotalCents(readNumber(SUBTOTAL_KEY));
  }, []);

  // Sincroniza entre abas.
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key === COUNT_KEY) setCount(readNumber(COUNT_KEY));
      if (event.key === SUBTOTAL_KEY) setSubtotalCents(readNumber(SUBTOTAL_KEY));
    }
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const addItem = useCallback<CartState['addItem']>((input) => {
    const qty = Math.max(1, input?.quantity ?? 1);
    const price = Math.max(0, input?.priceCents ?? 0);
    setCount((prev) => {
      const next = prev + qty;
      try {
        window.localStorage.setItem(COUNT_KEY, String(next));
      } catch {
        /* storage indisponível — badge só não persiste */
      }
      return next;
    });
    setSubtotalCents((prev) => {
      const next = prev + price * qty;
      try {
        window.localStorage.setItem(SUBTOTAL_KEY, String(next));
      } catch {
        /* idem */
      }
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setCount(0);
    setSubtotalCents(0);
    try {
      window.localStorage.removeItem(COUNT_KEY);
      window.localStorage.removeItem(SUBTOTAL_KEY);
    } catch {
      /* noop */
    }
  }, []);

  const value = useMemo<CartState>(
    () => ({ count, subtotalCents, addItem, clear }),
    [count, subtotalCents, addItem, clear],
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
