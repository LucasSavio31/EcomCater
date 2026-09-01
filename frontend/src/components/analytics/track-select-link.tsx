'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { track, type TrackItem } from '@/modules/analytics';

/**
 * `<Link>` que dispara `select_item` (GA4) / `SelectItem` (Meta) ao ser
 * clicado — para listas que não usam o `<ProductCard>` (ex.: resultados da
 * busca, que têm outro shape de dados).
 */
export function TrackSelectLink({
  href,
  item,
  listId,
  listName,
  index,
  className,
  children,
}: {
  href: string;
  item: TrackItem;
  listId?: string;
  listName?: string;
  index?: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={className}
      onClick={() =>
        track('select_item', {
          item_list_id: listId,
          item_list_name: listName,
          items: [{ ...item, index }],
        })
      }
    >
      {children}
    </Link>
  );
}
