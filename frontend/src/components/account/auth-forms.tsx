'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { useCart } from '@/modules/cart/cart-context';
import { track } from '@/modules/analytics';
import { isValidCpf, maskCpf, onlyDigits as digits } from '@/lib/cpf';
import { maskPhone } from '@/lib/phone';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Login + cadastro do cliente. Por decisão de projeto, a **senha é o CPF** —
 * o cliente entra com e-mail + CPF. Ao autenticar, funde o carrinho de convidado.
 */
export function AuthForms({ onDone }: { onDone?: () => void }) {
  const { login, register } = useAuth();
  const { refresh: refreshCart } = useCart();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form, setForm] = useState({ full_name: '', email: '', cpf: '', phone: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form, v: string) => setForm((p) => ({ ...p, [k]: v }));
  const cpfDigits = digits(form.cpf);

  // no login o CPF é só a senha (11 dígitos basta); no cadastro validamos os DV
  const cpfOk = mode === 'login' ? cpfDigits.length === 11 : isValidCpf(cpfDigits);
  const valid =
    EMAIL_RE.test(form.email) && cpfOk && (mode === 'login' || form.full_name.trim().length >= 2);

  async function submit() {
    if (!valid) return;
    setBusy(true);
    setError(null);
    const res =
      mode === 'login'
        ? await login(form.email.trim(), cpfDigits)
        : await register({
            full_name: form.full_name.trim(),
            email: form.email.trim(),
            password: cpfDigits,
            cpf: cpfDigits,
            phone: form.phone.trim() || undefined,
          });
    setBusy(false);
    if (!res.ok) {
      setError(res.error ?? 'Não foi possível continuar.');
      return;
    }
    if (mode === 'register') track('sign_up', {});
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
          label="CPF"
          inputMode="numeric"
          required
          value={form.cpf}
          onChange={(e) => set('cpf', maskCpf(e.target.value))}
          hint={mode === 'login' ? 'Seu CPF é a sua senha de acesso.' : 'Ele será a sua senha de acesso.'}
          error={
            form.cpf && cpfDigits.length === 11 && !cpfOk
              ? 'CPF inválido'
              : form.cpf && cpfDigits.length > 0 && cpfDigits.length < 11
                ? 'CPF incompleto'
                : undefined
          }
        />
        {mode === 'register' && (
          <Input
            label="Telefone (opcional)"
            inputMode="numeric"
            placeholder="(11) 99999-9999"
            value={form.phone}
            onChange={(e) => set('phone', maskPhone(e.target.value))}
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
