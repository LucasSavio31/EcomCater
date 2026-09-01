'use client';

import { useId, useState } from 'react';
import { Button, Input } from '@ecom/ui';
import { subscribeNewsletter } from '@/modules/newsletter/api';
import { track, identify } from '@/modules/analytics';

type Status = 'idle' | 'loading' | 'success' | 'error';

/** Captura de e-mail para a newsletter (bloco da home). */
export function NewsletterForm({
  compact = false,
  buttonColor,
  buttonTextColor,
}: {
  compact?: boolean;
  buttonColor?: string;
  buttonTextColor?: string;
}) {
  const nameId = useId();
  const emailId = useId();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState('');

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === 'loading') return;
    setStatus('loading');
    const result = await subscribeNewsletter({ email, name: name || undefined });
    if (result.ok) {
      identify({ email: email.trim(), firstName: name.trim().split(/\s+/)[0] || undefined });
      track('generate_lead', {});
      setStatus('success');
      setMessage('Pronto! Você vai receber nossas novidades.');
      setName('');
      setEmail('');
    } else {
      setStatus('error');
      setMessage(result.message);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2" noValidate>
      <div className={compact ? 'flex flex-col gap-2' : 'flex flex-col gap-2 sm:flex-row'}>
        {!compact && (
          <Input
            id={nameId}
            label="Nome"
            className="sm:flex-1"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            placeholder="Seu nome"
          />
        )}
        <Input
          id={emailId}
          label="E-mail"
          type="email"
          required
          className={compact ? '' : 'sm:flex-1'}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          placeholder="voce@email.com"
        />
        <div className="flex items-end">
          <Button
            type="submit"
            loading={status === 'loading'}
            block={compact}
            style={
              buttonColor ? { background: buttonColor, color: buttonTextColor } : undefined
            }
          >
            Inscrever
          </Button>
        </div>
      </div>
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
