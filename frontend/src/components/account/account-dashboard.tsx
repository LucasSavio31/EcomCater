'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Card, Input } from '@ecom/ui';
import { useAuth } from '@/modules/customer/auth-context';
import { customerApi } from '@/modules/customer/api';
import { maskPhone } from '@/lib/phone';
import { maskCpf } from '@/lib/cpf';

export function AccountDashboard() {
  const { customer, logout, reload } = useAuth();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    full_name: customer?.full_name ?? '',
    phone: customer?.phone ? maskPhone(customer.phone) : '',
    cpf: customer?.cpf ? maskCpf(customer.cpf) : '',
  });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (!customer) return null;

  async function save() {
    setBusy(true);
    setMsg(null);
    const res = await customerApi.updateMe({
      full_name: form.full_name.trim(),
      phone: form.phone.trim(),
      cpf: form.cpf.replace(/\D/g, '') || undefined,
    });
    setBusy(false);
    if (!res.ok) {
      setMsg(res.error.message);
      return;
    }
    await reload();
    setEditing(false);
  }

  return (
    <div className="flex flex-col gap-6">
      <Card variant="outline" className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-lg font-semibold">Olá, {customer.full_name.split(' ')[0]}!</p>
          <p className="text-sm text-text-muted">{customer.email}</p>
        </div>
        <Button variant="outline" onClick={() => void logout()}>
          Sair
        </Button>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/minha-conta/pedidos"
          className="rounded-card border border-surface-border p-4 text-sm font-medium hover:border-primary"
        >
          Meus pedidos
          <span className="mt-1 block text-xs font-normal text-text-muted">
            Acompanhe status, pagamento e envio.
          </span>
        </Link>
        <Link
          href="/minha-conta/enderecos"
          className="rounded-card border border-surface-border p-4 text-sm font-medium hover:border-primary"
        >
          Meus endereços
          <span className="mt-1 block text-xs font-normal text-text-muted">
            Cadastre e edite endereços de entrega.
          </span>
        </Link>
      </div>

      <Card variant="outline" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Meus dados</h2>
          {!editing && (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="text-sm text-primary underline"
            >
              Editar
            </button>
          )}
        </div>

        {!editing ? (
          <dl className="flex flex-col gap-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-text-muted">Nome:</dt>
              <dd>{customer.full_name}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-text-muted">Telefone:</dt>
              <dd>{customer.phone ? maskPhone(customer.phone) : '—'}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-text-muted">CPF:</dt>
              <dd>{customer.cpf ? maskCpf(customer.cpf) : '—'}</dd>
            </div>
          </dl>
        ) : (
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <Input
              label="Nome completo"
              value={form.full_name}
              onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Telefone"
                inputMode="numeric"
                placeholder="(11) 99999-9999"
                value={form.phone}
                onChange={(e) => setForm((p) => ({ ...p, phone: maskPhone(e.target.value) }))}
              />
              <Input
                label="CPF"
                inputMode="numeric"
                placeholder="000.000.000-00"
                value={form.cpf}
                onChange={(e) => setForm((p) => ({ ...p, cpf: maskCpf(e.target.value) }))}
              />
            </div>
            {msg && <p className="text-sm text-danger">{msg}</p>}
            <div className="flex gap-2">
              <Button type="submit" loading={busy}>
                Salvar
              </Button>
              <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
                Cancelar
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
