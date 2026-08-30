'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button, Input } from '@ecom/ui';
import { apiFetch } from '@/lib/api-client';
import { getCustomerToken } from '@/lib/customer-auth-storage';
import { useAuth } from '@/modules/customer/auth-context';

type Status = 'idle' | 'loading' | 'success' | 'error';

/**
 * Formulário de avaliação. Só clientes logados podem avaliar (a avaliação vai
 * para a fila de moderação). Deslogado → convite para entrar na Minha Conta.
 */
export function ReviewForm({ slug }: { slug: string }) {
  const { customer, loading: authLoading } = useAuth();
  const pathname = usePathname();
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState('');

  if (authLoading) return null;

  if (!customer) {
    return (
      <div className="flex flex-col gap-2 text-sm">
        <p className="text-text-muted">Só clientes com conta podem avaliar.</p>
        <Link
          href={`/minha-conta?redirect=${encodeURIComponent(pathname)}`}
          className="w-fit rounded-btn bg-primary px-4 py-2 font-semibold text-primary-fg"
        >
          Entrar para avaliar
        </Link>
      </div>
    );
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === 'loading') return;
    setStatus('loading');
    const res = await apiFetch(`/api/products/${encodeURIComponent(slug)}/reviews`, {
      method: 'POST',
      token: getCustomerToken(),
      body: { rating, title: title || null, body: body || null },
    });
    if (res.ok) {
      setStatus('success');
      setMessage('Obrigado! Sua avaliação será publicada após moderação.');
      setTitle('');
      setBody('');
      setRating(5);
    } else {
      setStatus('error');
      setMessage(
        res.error.status === 429
          ? 'Muitas avaliações em pouco tempo. Tente novamente mais tarde.'
          : res.error.status === 401
            ? 'Sua sessão expirou. Entre novamente.'
            : 'Não foi possível enviar sua avaliação.',
      );
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <p className="text-sm text-text-muted">
        Avaliando como <span className="font-medium text-text">{customer.full_name}</span>
      </p>
      <fieldset className="flex flex-col gap-1">
        <legend className="text-sm font-medium">Sua nota</legend>
        <div className="flex gap-1" role="radiogroup" aria-label="Nota de 1 a 5">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={rating === n}
              aria-label={`${n} ${n === 1 ? 'estrela' : 'estrelas'}`}
              onClick={() => setRating(n)}
              className={`min-h-touch min-w-touch rounded-card text-2xl leading-none ${
                n <= rating ? 'text-warning' : 'text-surface-border'
              }`}
            >
              ★
            </button>
          ))}
        </div>
      </fieldset>

      <Input label="Título (opcional)" value={title} onChange={(e) => setTitle(e.target.value)} />
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-text">Comentário (opcional)</span>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          className="w-full rounded-card border border-surface-border bg-surface px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
      </label>

      <Button type="submit" loading={status === 'loading'} className="self-start">
        Enviar avaliação
      </Button>

      {status === 'success' && (
        <p className="text-sm text-success" role="status">
          {message}
        </p>
      )}
      {status === 'error' && (
        <p className="text-sm text-danger" role="alert">
          {message}
        </p>
      )}
    </form>
  );
}
