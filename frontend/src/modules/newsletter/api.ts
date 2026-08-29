import { apiFetch } from '@/lib/api-client';

export interface NewsletterInput {
  email: string;
  name?: string;
}

export type NewsletterResult =
  | { ok: true }
  | { ok: false; message: string };

/** `POST /api/newsletter/subscribe` — usado no formulário da home (client). */
export async function subscribeNewsletter(input: NewsletterInput): Promise<NewsletterResult> {
  const res = await apiFetch<unknown>('/api/newsletter/subscribe', {
    method: 'POST',
    body: { email: input.email, name: input.name ?? null },
  });
  if (res.ok) return { ok: true };
  return {
    ok: false,
    message:
      res.error.status === 429
        ? 'Muitas tentativas. Tente novamente em instantes.'
        : res.error.message || 'Não foi possível concluir a inscrição.',
  };
}
