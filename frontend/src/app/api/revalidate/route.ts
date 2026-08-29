import { NextResponse } from 'next/server';
import { revalidateTag } from 'next/cache';

/**
 * Revalidação sob demanda das tags de cache do SSR (`theme`, `analytics`,
 * `menus`, `banners`…). O admin chama isto depois de salvar uma configuração
 * para a loja refletir sem esperar o `revalidate` nem reiniciar.
 *
 * Protegido por um segredo compartilhado quando `REVALIDATE_SECRET` está
 * definido; em dev local (sem o segredo) fica liberado.
 */
const ALLOWED_TAGS = new Set(['theme', 'analytics', 'menus', 'banners', 'settings']);

function authorized(req: Request): boolean {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret) return true;
  const header = req.headers.get('x-revalidate-secret');
  const url = new URL(req.url);
  return header === secret || url.searchParams.get('secret') === secret;
}

async function handle(req: Request) {
  if (!authorized(req)) {
    return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });
  }
  const url = new URL(req.url);
  const tags = (url.searchParams.get('tag') ?? '')
    .split(',')
    .map((t) => t.trim())
    .filter((t) => ALLOWED_TAGS.has(t));
  if (tags.length === 0) {
    return NextResponse.json({ ok: false, error: 'no valid tag' }, { status: 400 });
  }
  for (const tag of tags) revalidateTag(tag);
  return NextResponse.json({ ok: true, revalidated: tags });
}

export const GET = handle;
export const POST = handle;
