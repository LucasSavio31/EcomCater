'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Badge, Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox } from '@/components/form-controls';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { StatusBadge } from '@/components/status-badge';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { lookupCep } from '@/lib/viacep';
import { maskPhone } from '@/lib/phone';
import {
  customersApi,
  type CustomerAddress,
  type CustomerAddressInput,
  type CustomerDetail,
} from '@/modules/customers/api';

const maskCpf = (v: string) => {
  const d = v.replace(/\D/g, '').slice(0, 11);
  let o = d.slice(0, 3);
  if (d.length > 3) o += `.${d.slice(3, 6)}`;
  if (d.length > 6) o += `.${d.slice(6, 9)}`;
  if (d.length > 9) o += `-${d.slice(9)}`;
  return o;
};
const maskCep = (v: string) => {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
};

const EMPTY_ADDR: CustomerAddressInput = {
  label: 'Endereço',
  recipient_name: '',
  zip: '',
  street: '',
  number: '',
  complement: '',
  district: '',
  city: '',
  state: '',
  country: 'BR',
  is_default: false,
};

export default function ClienteDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();

  const fetcher = useCallback(() => customersApi.get(id), [id]);
  const { data, loading, error, reload, setData } = useResource<CustomerDetail>(fetcher, [id]);

  const [pf, setPf] = useState({ full_name: '', email: '', phone: '', cpf: '', is_active: true });
  const [savingPf, setSavingPf] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function deleteCustomer() {
    setDeleting(true);
    const res = await customersApi.remove(id);
    setDeleting(false);
    setConfirmDel(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success('Cliente excluído. O histórico de pedidos foi mantido.');
    router.push('/clientes');
  }

  useEffect(() => {
    if (data) {
      setPf({
        full_name: data.full_name,
        email: data.email,
        phone: data.phone ?? '',
        cpf: data.cpf ? maskCpf(data.cpf) : '',
        is_active: data.is_active,
      });
    }
  }, [data]);

  async function savePersonal() {
    setSavingPf(true);
    const res = await customersApi.update(id, {
      full_name: pf.full_name.trim(),
      email: pf.email.trim(),
      phone: pf.phone.trim() || null,
      cpf: pf.cpf.replace(/\D/g, '') || null,
      is_active: pf.is_active,
    });
    setSavingPf(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(
      res.data.orders_updated > 0
        ? `Salvo. ${res.data.orders_updated} pedido(s) ativo(s) atualizado(s).`
        : 'Dados salvos.',
    );
    reload();
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Cliente"
        back={
          <button
            type="button"
            onClick={() => router.push('/clientes')}
            className="self-start text-sm text-accent hover:underline"
          >
            ← Voltar para clientes
          </button>
        }
        actions={
          data ? (
            <Button
              size="sm"
              variant="ghost"
              className="text-danger"
              onClick={() => setConfirmDel(true)}
            >
              Excluir cliente
            </Button>
          ) : undefined
        }
      />

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        {data && (
          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <div className="flex flex-col gap-6">
              <Card variant="outline" className="flex flex-col gap-4">
                <h2 className="text-lg font-semibold">Dados pessoais</h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input
                    label="Nome completo"
                    value={pf.full_name}
                    onChange={(e) => setPf((s) => ({ ...s, full_name: e.target.value }))}
                  />
                  <Input
                    label="E-mail"
                    value={pf.email}
                    onChange={(e) => setPf((s) => ({ ...s, email: e.target.value }))}
                  />
                  <Input
                    label="Telefone"
                    inputMode="numeric"
                    placeholder="(11) 99999-9999"
                    value={maskPhone(pf.phone)}
                    onChange={(e) => setPf((s) => ({ ...s, phone: maskPhone(e.target.value) }))}
                  />
                  <Input
                    label="CPF"
                    inputMode="numeric"
                    placeholder="000.000.000-00"
                    value={pf.cpf}
                    onChange={(e) => setPf((s) => ({ ...s, cpf: maskCpf(e.target.value) }))}
                  />
                </div>
                <Checkbox
                  label="Conta ativa"
                  checked={pf.is_active}
                  onChange={(v) => setPf((s) => ({ ...s, is_active: v }))}
                />
                <p className="text-xs text-text-muted">
                  Salvar atualiza também os pedidos <b>ativos</b> (aguardando pagamento, pago,
                  em separação). Pedidos já enviados/entregues não mudam.
                </p>
                <Button loading={savingPf} onClick={() => void savePersonal()} className="self-start">
                  Salvar dados pessoais
                </Button>
              </Card>

              <Addresses
                customerId={id}
                addresses={data.addresses}
                onChanged={() => reload()}
              />
            </div>

            <Card variant="outline" className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold">Pedidos</h2>
              {data.orders.length === 0 && <p className="text-sm text-text-muted">Sem pedidos.</p>}
              <ul className="flex flex-col divide-y divide-surface-border">
                {data.orders.map((o) => (
                  <li key={o.number} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <Link href={`/pedidos/${o.number}`} className="font-medium text-accent hover:underline">
                      {o.number}
                    </Link>
                    <StatusBadge kind="order" value={o.status} />
                    {o.active && <Badge tone="accent">ativo</Badge>}
                    <span>{formatBRL(o.grand_total_cents)}</span>
                    <span className="text-text-muted">
                      {o.created_at ? formatDateTime(o.created_at) : '—'}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        )}
      </AsyncBoundary>

      <ConfirmDialog
        open={confirmDel}
        title="Excluir cliente"
        description="Remove o cadastro do cliente (dados pessoais e endereços). Os pedidos dele são preservados — ficam sem conta vinculada. Não pode ser desfeito."
        confirmLabel="Excluir"
        tone="danger"
        loading={deleting}
        onConfirm={() => void deleteCustomer()}
        onCancel={() => setConfirmDel(false)}
      />
    </div>
  );

  function Addresses({
    customerId,
    addresses,
    onChanged,
  }: {
    customerId: string;
    addresses: CustomerAddress[];
    onChanged: () => void;
  }) {
    const [form, setForm] = useState<CustomerAddressInput>(EMPTY_ADDR);
    const [editing, setEditing] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const [del, setDel] = useState<string | null>(null);
    const set = <K extends keyof CustomerAddressInput>(k: K, v: CustomerAddressInput[K]) =>
      setForm((f) => ({ ...f, [k]: v }));

    async function onCepBlur() {
      if (form.zip.replace(/\D/g, '').length !== 8) return;
      const found = await lookupCep(form.zip);
      if (!found) return;
      setForm((f) => ({
        ...f,
        street: found.street || f.street,
        district: found.district || f.district,
        city: found.city || f.city,
        state: found.state || f.state,
      }));
    }

    function edit(a: CustomerAddress) {
      setEditing(a.id);
      setForm({ ...a });
    }
    function resetForm() {
      setEditing(null);
      setForm(EMPTY_ADDR);
    }

    async function save() {
      if (!form.recipient_name.trim() || form.zip.replace(/\D/g, '').length !== 8) {
        return toast.error('Preencha destinatário e um CEP válido.');
      }
      setBusy(true);
      const payload = { ...form, zip: form.zip.replace(/\D/g, ''), state: form.state.toUpperCase() };
      const res = editing
        ? await customersApi.updateAddress(customerId, editing, payload)
        : await customersApi.addAddress(customerId, payload);
      setBusy(false);
      if (!res.ok) return toast.error(res.error.message);
      toast.success('Endereço salvo.');
      resetForm();
      onChanged();
    }

    async function remove() {
      if (!del) return;
      setBusy(true);
      const res = await customersApi.deleteAddress(customerId, del);
      setBusy(false);
      setDel(null);
      if (!res.ok) return toast.error(res.error.message);
      toast.success('Endereço removido.');
      onChanged();
    }

    return (
      <Card variant="outline" className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">Endereços</h2>
        {addresses.length === 0 && <p className="text-sm text-text-muted">Nenhum endereço.</p>}
        <ul className="flex flex-col gap-2">
          {addresses.map((a) => (
            <li
              key={a.id}
              className="flex flex-wrap items-center gap-2 rounded-card border border-surface-border p-3 text-sm"
            >
              <span className="font-medium">{a.label}</span>
              {a.is_default && <Badge tone="success">padrão</Badge>}
              <span className="text-text-muted">
                {a.street}, {a.number}
                {a.complement ? ` — ${a.complement}` : ''} · {a.district} · {a.city}/{a.state} · CEP{' '}
                {a.zip}
              </span>
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => edit(a)}>
                  Editar
                </Button>
                <Button size="sm" variant="ghost" className="text-danger" onClick={() => setDel(a.id)}>
                  Excluir
                </Button>
              </div>
            </li>
          ))}
        </ul>

        <div className="flex flex-col gap-3 border-t border-surface-border pt-4">
          <span className="text-sm font-medium">{editing ? 'Editar endereço' : 'Novo endereço'}</span>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Rótulo" value={form.label} onChange={(e) => set('label', e.target.value)} />
            <Input
              label="Destinatário"
              value={form.recipient_name}
              onChange={(e) => set('recipient_name', e.target.value)}
            />
            <Input
              label="CEP"
              inputMode="numeric"
              value={maskCep(form.zip)}
              onChange={(e) => set('zip', maskCep(e.target.value))}
              onBlur={() => void onCepBlur()}
            />
            <Input label="Rua" value={form.street} onChange={(e) => set('street', e.target.value)} />
            <Input label="Número" value={form.number} onChange={(e) => set('number', e.target.value)} />
            <Input
              label="Complemento"
              value={form.complement ?? ''}
              onChange={(e) => set('complement', e.target.value)}
            />
            <Input
              label="Bairro"
              value={form.district}
              onChange={(e) => set('district', e.target.value)}
            />
            <Input label="Cidade" value={form.city} onChange={(e) => set('city', e.target.value)} />
            <Input
              label="UF"
              value={form.state}
              onChange={(e) => set('state', e.target.value.toUpperCase().slice(0, 2))}
            />
          </div>
          <Checkbox
            label="Endereço padrão (aplica aos pedidos ativos)"
            checked={form.is_default}
            onChange={(v) => set('is_default', v)}
          />
          <div className="flex gap-2">
            <Button loading={busy} onClick={() => void save()}>
              {editing ? 'Salvar endereço' : 'Adicionar endereço'}
            </Button>
            {editing && (
              <Button variant="outline" onClick={resetForm}>
                Cancelar
              </Button>
            )}
          </div>
        </div>

        <ConfirmDialog
          open={del !== null}
          title="Excluir endereço"
          description="Remover este endereço do cliente?"
          confirmLabel="Excluir"
          tone="danger"
          loading={busy}
          onConfirm={() => void remove()}
          onCancel={() => setDel(null)}
        />
      </Card>
    );
  }
}
