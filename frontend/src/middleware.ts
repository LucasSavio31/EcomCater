import { NextResponse, type NextRequest } from 'next/server';
import { DEFAULT_SITE, normalizeHost, siteOrigin } from '@/lib/site';

/**
 * Multi-domínio + redirects de produto renomeado.
 *
 * 1. Domínio (site): cada domínio ATIVO em Infraestrutura → Domínios é um site
 *    independente. `/<rota>` é reescrito (internamente, a URL não muda) pra
 *    `/<site>/<rota>` — segmento `app/[site]` —, então cada domínio tem o
 *    próprio cache de página, canonical, SEO e tags. Host desconhecido, IP e
 *    localhost caem no domínio padrão (o do build). O site vai também no
 *    header `x-site` pra `robots.txt`/`sitemap.xml`/`llms.txt` (fora do
 *    segmento).
 * 2. Produto renomeado: `/produto/<slug-antigo>` -> 308 pro slug atual ANTES
 *    de a página começar a ser enviada (na PDP o `permanentRedirect` sozinho
 *    vira meta-refresh 200 por causa do streaming do `loading.tsx`).
 * 3. Domínio marcado "não indexar" (Rastreamento): `X-Robots-Tag: noindex`.
 *
 * Os mapas vêm da API e ficam em memória por 1–5 min. Se a API falhar, segue
 * com o último mapa conhecido (ou nenhum) — nunca bloqueia a página.
 */
export const config = {
  // tudo menos API interna, assets do Next e arquivos estáticos com extensão
  // (robots.txt/sitemap.xml/llms.txt passam: precisam do x-site)
  matcher: [
    '/((?!api/|_next/|icons/|sw\\.js|favicon\\.ico|.*\\.(?:png|jpe?g|gif|webp|avif|svg|ico|css|js|map|woff2?|ttf)$).*)',
  ],
  runtime: 'nodejs',
};

// arquivos na raiz de `app/` (fora de [site]) — não reescreve, só marca o site
const ROOT_FILES = new Set(['/robots.txt', '/sitemap.xml', '/llms.txt', '/manifest.webmanifest']);

type Cached<T> = { at: number; value: T } | null;

function apiBase(): string {
  return (
    process.env.API_URL_INTERNAL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    'http://localhost:8000'
  );
}

async function cachedJson<T>(
  cache: { current: Cached<T> },
  path: string,
  ttlMs: number,
  empty: T,
): Promise<T> {
  const c = cache.current;
  if (c && Date.now() - c.at < ttlMs) return c.value;
  try {
    const res = await fetch(`${apiBase()}${path}`, {
      signal: AbortSignal.timeout(1500),
      cache: 'no-store',
    });
    cache.current = { at: Date.now(), value: res.ok ? ((await res.json()) as T) : (c?.value ?? empty) };
  } catch {
    // API fora: mantém o anterior e só tenta de novo no próximo TTL
    cache.current = { at: Date.now(), value: c?.value ?? empty };
  }
  return cache.current.value;
}

const sitesCache: { current: Cached<{ primary: string | null; hosts: string[] }> } = { current: null };
const redirectsCache: { current: Cached<Record<string, string>> } = { current: null };
const noindexCache = new Map<string, { current: Cached<{ seo_noindex?: boolean }> }>();

async function resolveSite(req: NextRequest): Promise<string> {
  const host = normalizeHost(req.headers.get('x-forwarded-host') ?? req.headers.get('host'));
  if (!host || host === DEFAULT_SITE) return DEFAULT_SITE;
  const sites = await cachedJson(sitesCache, '/api/domains/sites', 60_000, { primary: null, hosts: [] });
  return sites.hosts.includes(host) ? host : DEFAULT_SITE;
}

async function isNoindex(site: string): Promise<boolean> {
  let slot = noindexCache.get(site);
  if (!slot) {
    slot = { current: null };
    noindexCache.set(site, slot);
  }
  const cfg = await cachedJson(slot, `/api/analytics/config?site=${encodeURIComponent(site)}`, 60_000, {});
  return !!cfg.seo_noindex;
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const site = await resolveSite(req);

  // 2. produto renomeado -> 308 (antes de qualquer render), no MESMO domínio
  if (pathname.startsWith('/produto/')) {
    const slug = decodeURIComponent(pathname.split('/')[2] ?? '');
    const map = await cachedJson(redirectsCache, '/api/products/slug-redirects', 300_000, {});
    const target = slug ? map[slug] : undefined;
    if (target && target !== slug) {
      return NextResponse.redirect(`${siteOrigin(site)}/produto/${target}${req.nextUrl.search}`, 308);
    }
  }

  // 1. domínio -> /<site>/<rota>
  const headers = new Headers(req.headers);
  headers.set('x-site', site);

  let res: NextResponse;
  if (ROOT_FILES.has(pathname)) {
    res = NextResponse.next({ request: { headers } });
  } else {
    const url = req.nextUrl.clone();
    url.pathname = `/${site}${pathname === '/' ? '' : pathname}`;
    res = NextResponse.rewrite(url, { request: { headers } });
  }

  // 3. domínio fora do Google
  if (await isNoindex(site)) res.headers.set('X-Robots-Tag', 'noindex, nofollow');
  return res;
}
