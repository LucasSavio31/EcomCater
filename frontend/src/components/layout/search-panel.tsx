'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { searchProducts } from '@/modules/catalog/api';
import type { SearchResultItem } from '@/modules/catalog/types';
import { resolveMediaUrl } from '@/lib/media';
import { formatBRL } from '@/lib/format';
import { CloseIcon, SearchIcon } from '@/components/icons';

interface SearchPanelProps {
  open: boolean;
  onClose: () => void;
}

/** Campo de busca com typeahead (debounce 250ms) e dropdown de resultados. */
export function SearchPanel({ open, onClose }: SearchPanelProps) {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    if (open) inputRef.current?.focus();
    else {
      setTerm('');
      setResults([]);
      setActive(-1);
    }
  }, [open]);

  useEffect(() => {
    const q = term.trim();
    if (q.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const handle = window.setTimeout(async () => {
      const data = await searchProducts(q, 8);
      setResults(data);
      setActive(-1);
      setLoading(false);
    }, 250);
    return () => window.clearTimeout(handle);
  }, [term]);

  if (!open) return null;

  const submit = (value: string) => {
    const q = value.trim();
    if (!q) return;
    onClose();
    router.push(`/busca?q=${encodeURIComponent(q)}`);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (event.key === 'Enter') {
      const chosen = results[active];
      if (chosen) {
        onClose();
        router.push(chosen.url);
      } else {
        submit(term);
      }
    } else if (event.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="border-t border-surface-border bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-3">
        <div className="relative">
          <form
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              submit(term);
            }}
            className="flex items-center gap-2 rounded-card border border-surface-border px-3"
          >
            <SearchIcon className="h-5 w-5 shrink-0 text-text-muted" />
            <input
              ref={inputRef}
              type="search"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="O que você procura?"
              aria-label="Buscar produtos"
              role="combobox"
              aria-expanded={results.length > 0}
              aria-controls={listId}
              aria-autocomplete="list"
              className="min-h-touch w-full bg-transparent text-sm text-text outline-none placeholder:text-text-muted"
            />
            <button
              type="button"
              onClick={onClose}
              aria-label="Fechar busca"
              className="min-h-touch min-w-touch rounded-card p-1 text-text-muted hover:text-text"
            >
              <CloseIcon className="h-5 w-5" />
            </button>
          </form>

          {(loading || results.length > 0 || term.trim().length >= 2) && (
            <ul
              id={listId}
              role="listbox"
              className="absolute left-0 right-0 top-full z-30 mt-1 max-h-[70vh] overflow-y-auto rounded-card border border-surface-border bg-surface py-1 shadow-lg"
            >
              {loading && (
                <li className="px-3 py-2 text-sm text-text-muted">Buscando…</li>
              )}
              {!loading && results.length === 0 && term.trim().length >= 2 && (
                <li className="px-3 py-2 text-sm text-text-muted">Nada encontrado para “{term}”.</li>
              )}
              {results.map((item, i) => {
                const img = resolveMediaUrl(item.image_url);
                return (
                  <li key={`${item.type}-${item.id}`} role="option" aria-selected={i === active}>
                    <Link
                      href={item.url}
                      onClick={onClose}
                      className={`flex items-center gap-3 px-3 py-2 text-sm ${i === active ? 'bg-bg-subtle' : 'hover:bg-bg-subtle'}`}
                    >
                      <span className="relative h-10 w-10 shrink-0 overflow-hidden rounded-card bg-bg-subtle">
                        {img && (
                          <Image src={img} alt="" fill sizes="40px" className="object-cover" />
                        )}
                      </span>
                      <span className="flex-1">
                        <span className="block text-text">{item.name}</span>
                        {item.type === 'category' && (
                          <span className="text-xs text-text-muted">Categoria</span>
                        )}
                      </span>
                      {typeof item.price_cents === 'number' && (
                        <span className="text-sm font-medium text-text">
                          {formatBRL(item.price_cents)}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
              {results.length > 0 && (
                <li>
                  <button
                    type="button"
                    onClick={() => submit(term)}
                    className="w-full px-3 py-2 text-left text-sm font-medium text-primary hover:bg-bg-subtle"
                  >
                    Ver todos os resultados para “{term}”
                  </button>
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
