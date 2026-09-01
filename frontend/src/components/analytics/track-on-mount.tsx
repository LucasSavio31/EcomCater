'use client';

import { useEffect, useRef } from 'react';
import { track, type TrackEvent, type TrackItem } from '@/modules/analytics';

interface Props {
  event: TrackEvent;
  items?: TrackItem[];
  value?: number;
  currency?: string;
  searchTerm?: string;
  itemListId?: string;
  itemListName?: string;
  /** chave que, se mudar, permite disparar de novo (ex.: slug do produto). */
  dedupeKey?: string;
}

/**
 * Dispara um evento de rastreamento uma vez, quando o componente monta
 * (ou quando `dedupeKey` muda). Para eventos de visualização de página:
 * `view_item`, `view_item_list`, `search`, `view_cart`, `begin_checkout`.
 */
export function TrackOnMount({
  event,
  items,
  value,
  currency,
  searchTerm,
  itemListId,
  itemListName,
  dedupeKey,
}: Props) {
  const sent = useRef<string | null>(null);

  useEffect(() => {
    const key = dedupeKey ?? event;
    if (sent.current === key) return;
    sent.current = key;
    track(event, {
      items,
      value,
      currency,
      search_term: searchTerm,
      item_list_id: itemListId,
      item_list_name: itemListName,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event, dedupeKey]);

  return null;
}
