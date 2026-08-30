'use client';

/**
 * Pede à loja (Next.js) para revalidar as tags de cache do SSR depois que uma
 * configuração muda no admin. Best-effort: falha aqui não quebra o salvamento.
 */
const STORE_URL =
  process.env.NEXT_PUBLIC_STORE_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

export async function revalidateStore(...tags: string[]): Promise<void> {
  if (tags.length === 0) return;
  const url = `${STORE_URL}/api/revalidate?tag=${encodeURIComponent(tags.join(','))}`;
  try {
    // `no-cors`: a loja (:3000) e o admin (:3001) são origens diferentes; sem
    // isto o fetch rejeitaria por CORS e a revalidação não aconteceria.
    await fetch(url, { method: 'POST', mode: 'no-cors', cache: 'no-store', keepalive: true });
  } catch {
    /* loja pode estar fora no dev — sem problema */
  }
}
