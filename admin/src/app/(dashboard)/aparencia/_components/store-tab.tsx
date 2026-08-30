'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@ecom/ui';
import { Textarea } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { appearanceApi, type StoreSettings } from '@/modules/appearance/api';
import { lookupCep } from '@/lib/viacep';
import { maskPhone } from '@/lib/phone';
import { CurrencyField } from '@/components/currency-field';

const ADDRESS_FIELDS: Array<{ key: string; label: string }> = [
  { key: 'zip', label: 'CEP' },
  { key: 'street', label: 'Logradouro' },
  { key: 'number', label: 'Número' },
  { key: 'complement', label: 'Complemento' },
  { key: 'district', label: 'Bairro' },
  { key: 'city', label: 'Cidade' },
  { key: 'state', label: 'UF' },
];

const SOCIAL_FIELDS = ['instagram', 'facebook', 'tiktok', 'youtube'];

export function StoreTab() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useResource(() => appearanceApi.getSettings());
  const [draft, setDraft] = useState<StoreSettings | null>(null);
  const [saving, setSaving] = useState(false);

  const settings = draft ?? data;
  const set = <K extends keyof StoreSettings>(k: K, v: StoreSettings[K]): void => {
    if (!settings) return;
    setDraft({ ...settings, [k]: v });
  };
  const setAddress = (key: string, value: string): void => {
    if (!settings) return;
    setDraft({ ...settings, address_json: { ...(settings.address_json ?? {}), [key]: value } });
  };
  const setSocial = (key: string, value: string): void => {
    if (!settings) return;
    setDraft({ ...settings, social_json: { ...(settings.social_json ?? {}), [key]: value } });
  };
  async function onCepBlur(): Promise<void> {
    const base = draft ?? data;
    if (!base) return;
    const zip = String(base.address_json?.zip ?? '').replace(/\D/g, '');
    if (zip.length !== 8) return;
    const found = await lookupCep(zip);
    if (!found) return;
    const a = { ...(base.address_json ?? {}) };
    a.street = a.street || found.street;
    a.district = a.district || found.district;
    a.city = a.city || found.city;
    a.state = a.state || found.state;
    setDraft({ ...base, address_json: a });
  }

  async function save(): Promise<void> {
    if (!settings) return;
    setSaving(true);
    const result = await appearanceApi.putSettings(settings);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Dados da loja salvos.');
    setData(result.data);
    setDraft(null);
  }

  return (
    <AsyncBoundary loading={loading} error={error} onRetry={reload}>
      {settings && (
        <div className="flex flex-col gap-6">
          <Card variant="outline" className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Identificação</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Nome da loja" value={settings.store_name} onChange={(e) => set('store_name', e.target.value)} />
              <Input
                label="Razão social"
                value={settings.legal_name ?? ''}
                onChange={(e) => set('legal_name', e.target.value)}
              />
              <Input label="CNPJ" value={settings.cnpj ?? ''} onChange={(e) => set('cnpj', e.target.value)} />
              <Input
                label="Telefone"
                inputMode="numeric"
                placeholder="(11) 99999-9999"
                value={maskPhone(settings.contact_phone ?? '')}
                onChange={(e) => set('contact_phone', maskPhone(e.target.value))}
              />
              <Input
                label="WhatsApp"
                inputMode="numeric"
                placeholder="(11) 99999-9999"
                value={maskPhone(settings.contact_whatsapp ?? '')}
                onChange={(e) => set('contact_whatsapp', maskPhone(e.target.value))}
              />
              <CurrencyField
                label="Frete grátis a partir de (R$)"
                cents={settings.free_shipping_threshold_cents}
                onChange={(c) => set('free_shipping_threshold_cents', c)}
              />
            </div>
          </Card>

          <Card variant="outline" className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Endereço</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              {ADDRESS_FIELDS.map((f) => (
                <Input
                  key={f.key}
                  label={f.label}
                  value={settings.address_json?.[f.key] ?? ''}
                  onChange={(e) => setAddress(f.key, e.target.value)}
                  onBlur={f.key === 'zip' ? () => void onCepBlur() : undefined}
                />
              ))}
            </div>
          </Card>

          <Card variant="outline" className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Redes sociais</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {SOCIAL_FIELDS.map((key) => (
                <Input
                  key={key}
                  label={key[0]?.toUpperCase() + key.slice(1)}
                  value={settings.social_json?.[key] ?? ''}
                  onChange={(e) => setSocial(key, e.target.value)}
                />
              ))}
            </div>
          </Card>

          <Card variant="outline" className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Bandeiras de pagamento (rodapé)</h2>
            <Textarea
              label="Bandeiras (uma por linha)"
              rows={4}
              value={(settings.payment_flags_json ?? []).join('\n')}
              onChange={(e) =>
                set(
                  'payment_flags_json',
                  e.target.value
                    .split('\n')
                    .map((s) => s.trim())
                    .filter(Boolean),
                )
              }
            />
          </Card>

          <Button loading={saving} onClick={() => void save()} className="self-start">
            Salvar dados da loja
          </Button>
        </div>
      )}
    </AsyncBoundary>
  );
}
