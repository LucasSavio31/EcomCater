'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { trackPageView } from './tracker';

/**
 * Dispara `page_view` / `PageView` a cada troca de rota no App Router.
 * O primeiro carregamento já é coberto pelas tags base no `<head>`, então
 * pulamos a montagem inicial.
 */
export function AnalyticsRouteTracker() {
  const pathname = usePathname();
  const search = useSearchParams();
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const qs = search.toString();
    trackPageView(qs ? `${pathname}?${qs}` : pathname);
  }, [pathname, search]);

  return null;
}
