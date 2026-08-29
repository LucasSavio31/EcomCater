'use client';

/**
 * Pede à loja (Next.js) para revalidar as tags de cache do SSR depois que uma
 * configuração muda no admin. Best-effort: falha aqui não quebra o salvamento.
 */
const STORE_URL =
  process.env.NEXT_PUBLIC_STORE_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

export async function revalidateStore(...tags: string[]): Promise<void> {
  if (tags.length === 0) return;
  try {
    await fetch(`${STORE_URL}/api/revalidate?tag=${encodeURIComponent(tags.join(','))}`, {
      method: 'POST',
      cache: 'no-store',
    });
  } catch {
    /* loja pode estar fora no dev — sem problema */
  }
}
