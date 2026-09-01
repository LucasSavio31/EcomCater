'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Favoritos — PLACEHOLDER local (Fase 3). Guarda ids em `localStorage`.
 * A Fase 4+ liga em `wishlists`/`wishlist_items` da API.
 */
const KEY = 'ecom:wishlist';

function read(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : []);
  } catch {
    return new Set();
  }
}

export function useWishlist() {
  const [ids, setIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setIds(read());
  }, []);

  const persist = useCallback((next: Set<string>) => {
    setIds(new Set(next));
    try {
      window.localStorage.setItem(KEY, JSON.stringify([...next]));
    } catch {
      /* storage indisponível */
    }
  }, []);

  const has = useCallback((id: string) => ids.has(id), [ids]);

  const toggle = useCallback(
    (id: string) => {
      const next = new Set(ids);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      persist(next);
    },
    [ids, persist],
  );

  /** Remove vários ids de uma vez (ex.: favoritos que não existem mais). */
  const prune = useCallback(
    (remove: string[]) => {
      if (remove.length === 0) return;
      const next = new Set(ids);
      let changed = false;
      for (const id of remove) if (next.delete(id)) changed = true;
      if (changed) persist(next);
    },
    [ids, persist],
  );

  return { ids, has, toggle, prune };
}
