'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiResult } from './admin-api-client';

interface ResourceState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  setData: (updater: T | ((prev: T | null) => T | null)) => void;
}

/**
 * Busca um recurso via `adminFetch` e devolve estado de loading/erro/dados.
 * `deps` dispara nova busca quando mudam (ex. filtros, página).
 */
export function useResource<T>(
  fetcher: () => Promise<ApiResult<T>>,
  deps: ReadonlyArray<unknown> = [],
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void (async () => {
      const result = await fetcherRef.current();
      if (!active) return;
      if (result.ok) {
        setData(result.data);
      } else {
        setError(result.error.message);
      }
      setLoading(false);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  return { data, loading, error, reload, setData };
}

/** Executa uma mutação e devolve `{ run, loading, error }`. */
export function useMutation<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<ApiResult<TResult>>,
): {
  run: (...args: TArgs) => Promise<ApiResult<TResult>>;
  loading: boolean;
  error: string | null;
} {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (...args: TArgs) => {
      setLoading(true);
      setError(null);
      const result = await fn(...args);
      if (!result.ok) setError(result.error.message);
      setLoading(false);
      return result;
    },
    [fn],
  );

  return { run, loading, error };
}
