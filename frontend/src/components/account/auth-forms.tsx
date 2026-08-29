'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { useCart } from '@/modules/cart/cart-context';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Login + cadastro em uma aba só. Ao autenticar, refunde o carrinho de convidado. */
export function AuthForms({ onDone }: { onDone?: () => void }) {
  const { login, register } = useAuth();
  const { refresh: refreshCart } = useCart();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({ full_name: '', email: '', password: '', phone: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const valid =
    EMAIL_RE.test(form.email) &&
    form.password.length >= 8 &&
    (mode === 'login' || form.full_name.trim().length >= 2);

  async function submit() {
    if (!valid) return;
    setBusy(true);
    setError(null);
    const res =
      mode === 'login'
        ? await login(form.email.trim(), form.password)
        : await register({
            full_name: form.full_name.trim(),
            email: form.email.trim(),
            password: form.password,
            phone: form.phone.trim() || undefined,
          });
    setBusy(false);
    if (!res.ok) {
      setError(res.error ?? 'Não foi possível continuar.');
      return;
    }
    await refreshCart();
    onDone?.();
  }

  return (
    <Card variant="outline" className="mx-auto flex w-full max-w-md flex-col gap-4">
      <div className="flex gap-2">
        {(['login', 'register'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setError(null);
            }}
            className={`min-h-touch flex-1 rounded-card border px-3 text-sm font-medium transition ${
              mode === m ? 'border-primary bg-primary/5' : 'border-surface-border'
            }`}
          >
            {m === 'login' ? 'Entrar' : 'Criar conta'}
          </button>
        ))}
      </div>

      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {mode === 'register' && (
          <Input
            label="Nome completo"
            required
            value={form.full_name}
            onChange={(e) => set('full_name', e.target.value)}
          />
        )}
        <Input
          label="E-mail"
          type="email"
          required
          value={form.email}
          onChange={(e) => set('email', e.target.value)}
          error={form.email && !EMAIL_RE.test(form.email) ? 'E-mail inválido' : undefined}
        />
        <Input
          label="Senha"
          type="password"
          required
          value={form.password}
          onChange={(e) => set('password', e.target.value)}
          hint={mode === 'register' ? 'Mínimo de 8 caracteres.' : undefined}
          error={form.password && form.password.length < 8 ? 'Mínimo de 8 caracteres' : undefined}
        />
        {mode === 'register' && (
          <Input
            label="Telefone (opcional)"
            value={form.phone}
            onChange={(e) => set('phone', e.target.value)}
          />
        )}

        {error && <p className="text-sm text-danger">{error}</p>}

        <Button type="submit" block loading={busy} disabled={!valid}>
          {mode === 'login' ? 'Entrar' : 'Criar conta'}
        </Button>
      </form>
    </Card>
  );
}
