'use client';

import { useEffect, useState } from 'react';
import { Button, Card, Input, Spinner } from '@ecom/ui';
import { customerApi } from '@/modules/customer/api';
import type { Address, AddressInput } from '@/modules/customer/types';
import { lookupCep } from '@/lib/viacep';
import { maskHouseNumber } from '@/lib/address';

const maskCep = (v: string) => {
  const d = v.replace(/\D/g, '').slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
};

const BLANK: AddressInput = {
  label: 'Casa',
  recipient_name: '',
  zip: '',
  street: '',
  number: '',
  complement: '',
  district: '',
  city: '',
  state: '',
  is_default: false,
};

export function AddressesManager() {
  const [list, setList] = useState<Address[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | 'new' | null>(null);
  const [form, setForm] = useState<AddressInput>(BLANK);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const res = await customerApi.listAddresses();
    if (res.ok) setList(res.data);
    else setError(res.error.message);
  }

  useEffect(() => {
    void reload();
  }, []);

  function startNew() {
    setForm(BLANK);
    setEditingId('new');
  }
  function startEdit(a: Address) {
    setForm({ ...a, complement: a.complement ?? '' });
    setEditingId(a.id);
  }
  const set = (k: keyof AddressInput, v: string | boolean) => setForm((p) => ({ ...p, [k]: v }));

  async function onCepBlur() {
    const found = await lookupCep(form.zip);
    if (found) {
      setForm((p) => ({
        ...p,
        street: found.street || p.street,
        district: found.district || p.district,
        city: found.city || p.city,
        state: found.state || p.state,
      }));
    }
  }

  const valid =
    form.recipient_name.trim() !== '' &&
    form.zip.replace(/\D/g, '').length === 8 &&
    form.street.trim() !== '' &&
    form.number.trim() !== '' &&
    form.district.trim() !== '' &&
    form.city.trim() !== '' &&
    form.state.trim().length === 2;

  async function save() {
    if (!valid) return;
    setBusy(true);
    setError(null);
    const payload: AddressInput = {
      ...form,
      zip: form.zip.replace(/\D/g, ''),
      state: form.state.toUpperCase(),
      complement: form.complement?.trim() || null,
    };
    const res =
      editingId === 'new'
        ? await customerApi.createAddress(payload)
        : await customerApi.updateAddress(editingId as string, payload);
    setBusy(false);
    if (!res.ok) {
      setError(res.error.message);
      return;
    }
    setEditingId(null);
    await reload();
  }

  async function remove(id: string) {
    setBusy(true);
    await customerApi.deleteAddress(id);
    setBusy(false);
    await reload();
  }

  if (!list) {
    return (
      <p className="flex items-center gap-2 py-16 text-text-muted">
        <Spinner /> Carregando endereços…
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <p className="text-sm text-danger">{error}</p>}

      <ul className="flex flex-col gap-3">
        {list.map((a) => (
          <li key={a.id}>
            <Card variant="outline" className="flex flex-wrap items-start justify-between gap-3">
              <div className="text-sm">
                <p className="font-medium">
                  {a.label}
                  {a.is_default && (
                    <span className="ml-2 rounded-card bg-bg-subtle px-2 py-0.5 text-xs">Padrão</span>
                  )}
                </p>
                <p className="text-text-muted">
                  {a.recipient_name} — {a.street}, {a.number}
                  {a.complement ? ` (${a.complement})` : ''}, {a.district}, {a.city}/{a.state}, CEP{' '}
                  {a.zip}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => startEdit(a)}
                  className="text-sm text-primary underline"
                >
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => void remove(a.id)}
                  disabled={busy}
                  className="text-sm text-text-muted underline hover:text-danger"
                >
                  Excluir
                </button>
              </div>
            </Card>
          </li>
        ))}
      </ul>

      {editingId === null ? (
        <Button variant="outline" onClick={startNew}>
          + Adicionar endereço
        </Button>
      ) : (
        <Card variant="outline" className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">
            {editingId === 'new' ? 'Novo endereço' : 'Editar endereço'}
          </h2>
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Input label="Rótulo" value={form.label} onChange={(e) => set('label', e.target.value)} />
              <Input
                label="Nome de quem recebe"
                required
                value={form.recipient_name}
                onChange={(e) => set('recipient_name', e.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="CEP"
                inputMode="numeric"
                required
                value={form.zip}
                onChange={(e) => set('zip', maskCep(e.target.value))}
                onBlur={() => void onCepBlur()}
              />
              <Input
                label="Número"
                required
                inputMode="numeric"
                placeholder="Nº ou S/N"
                value={form.number}
                onChange={(e) => set('number', maskHouseNumber(e.target.value))}
              />
            </div>
            <Input
              label="Rua / logradouro"
              required
              value={form.street}
              onChange={(e) => set('street', e.target.value)}
            />
            <Input
              label="Complemento (opcional)"
              value={form.complement ?? ''}
              onChange={(e) => set('complement', e.target.value)}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Bairro"
                required
                value={form.district}
                onChange={(e) => set('district', e.target.value)}
              />
              <Input
                label="Cidade"
                required
                value={form.city}
                onChange={(e) => set('city', e.target.value)}
              />
            </div>
            <Input
              label="Estado (UF)"
              required
              maxLength={2}
              value={form.state}
              onChange={(e) => set('state', e.target.value.toUpperCase().slice(0, 2))}
              className="sm:w-32"
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => set('is_default', e.target.checked)}
              />
              Usar como endereço padrão
            </label>

            <div className="flex gap-2">
              <Button type="submit" loading={busy} disabled={!valid}>
                Salvar
              </Button>
              <Button type="button" variant="ghost" onClick={() => setEditingId(null)}>
                Cancelar
              </Button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
