import { NextResponse, type NextRequest } from 'next/server';

/**
 * Produto renomeado: `/produto/<slug-antigo>` -> 308 pro slug atual ANTES de
 * a página começar a ser enviada. (Na PDP o `permanentRedirect` sozinho vira
 * meta-refresh com status 200 por causa do streaming do `loading.tsx` — pro
 * Google/Merchant Center o certo é o 308 no cabeçalho.)
 *
 * O mapa antigo->novo é pequeno; fica em memória por 5 min. Se a API falhar,
 * segue sem redirecionar (a PDP ainda resolve o slug antigo como fallback).
 */
export const config = {
  matcher: '/produto/:slug*',
  runtime: 'nodejs',
};

const TTL_MS = 5 * 60 * 1000;
let cache: { at: number; map: Record<string, string> } | null = null;

function apiBase(): string {
  return (
    process.env.API_URL_INTERNAL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    'http://localhost:8000'
  );
}

async function redirects(): Promise<Record<string, string>> {
  if (cache && Date.now() - cache.at < TTL_MS) return cache.map;
  try {
    const res = await fetch(`${apiBase()}/api/products/slug-redirects`, {
      signal: AbortSignal.timeout(1500),
      cache: 'no-store',
    });
    if (res.ok) cache = { at: Date.now(), map: (await res.json()) as Record<string, string> };
    else cache = { at: Date.now(), map: cache?.map ?? {} };
  } catch {
    // API fora: mantém o mapa anterior (ou nenhum) e só tenta de novo no próximo TTL
    cache = { at: Date.now(), map: cache?.map ?? {} };
  }
  return cache.map;
}

export async function middleware(req: NextRequest) {
  const slug = decodeURIComponent(req.nextUrl.pathname.split('/')[2] ?? '');
  if (!slug) return NextResponse.next();
  const target = (await redirects())[slug];
  if (!target || target === slug) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = `/produto/${target}`;
  return NextResponse.redirect(url, 308);
}
