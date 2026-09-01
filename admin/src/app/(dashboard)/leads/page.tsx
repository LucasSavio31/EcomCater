'use client';

import { useMemo, useState } from 'react';
import { Badge, Button, Card, Input, Modal } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Select } from '@/components/form-controls';
import { AsyncBoundary } from '@/components/async-boundary';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatDateTime, formatNumber } from '@/lib/format';
import { leadsApi, SOURCE_LABEL } from '@/modules/leads/api';
import { promotionsApi } from '@/modules/promotions/api';

export default function LeadsPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useResource(() => leadsApi.list());
  const stats = useResource(() => leadsApi.stats());
  const coupons = useResource(() => promotionsApi.list());
  const [source, setSource] = useState('');
  const [quick, setQuick] = useState<'' | 'checkout' | 'popup' | 'coupon'>('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmDel, setConfirmDel] = useState(false);
  const [campaignOpen, setCampaignOpen] = useState(false);
  const [campaignAll, setCampaignAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [couponCode, setCouponCode] = useState('');

  const rows = useMemo(() => {
    let all = data ?? [];
    if (source) all = all.filter((l) => l.source === source);
    if (quick === 'checkout') all = all.filter((l) => l.source === 'checkout');
    else if (quick === 'popup')
      all = all.filter((l) => l.source === 'popup' || l.source === 'lead_popup');
    else if (quick === 'coupon') all = all.filter((l) => !!l.coupon_code);
    return all;
  }, [data, source, quick]);

  function applyQuick(key: 'checkout' | 'popup' | 'coupon') {
    setSource('');
    setQuick((cur) => (cur === key ? '' : key));
  }

  const sources = useMemo(
    () => Array.from(new Set((data ?? []).map((l) => l.source))),
    [data],
  );
  const allChecked = rows.length > 0 && rows.every((l) => selected.has(l.id));
  const selectedList = [...selected];

  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allChecked) rows.forEach((l) => n.delete(l.id));
      else rows.forEach((l) => n.add(l.id));
      return n;
    });

  async function doDelete() {
    setBusy(true);
    const res = await leadsApi.remove(selectedList);
    setBusy(false);
    setConfirmDel(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`${res.data.deleted} lead(s) excluído(s).`);
    setSelected(new Set());
    reload();
    stats.reload();
  }

  function openCampaign(all: boolean) {
    setCampaignAll(all);
    setCampaignOpen(true);
  }

  const campaignTargetCount = campaignAll ? (stats.data?.subscribed ?? 0) : selected.size;

  async function sendCampaign() {
    if (!subject.trim() || !body.trim()) {
      toast.error('Preencha o assunto e o conteúdo.');
      return;
    }
    setBusy(true);
    const res = await leadsApi.campaign({
      ids: campaignAll ? [] : selectedList,
      to_all: campaignAll,
      subject: subject.trim(),
      body: body.trim(),
      coupon_code: couponCode || null,
    });
    setBusy(false);
    if (!res.ok) return toast.error(res.error.message);
    toast.success(`Campanha enviada: ${res.data.sent} ok, ${res.data.failed} falha(s).`);
    setCampaignOpen(false);
    setSubject('');
    setBody('');
    setCouponCode('');
  }

  function exportCsv() {
    const head = ['nome', 'email', 'telefone', 'origem', 'cupom', 'data'];
    const lines = rows.map((l) =>
      [l.name ?? '', l.email, l.phone ?? '', SOURCE_LABEL[l.source] ?? l.source, l.coupon_code ?? '', l.created_at ?? '']
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(','),
    );
    const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leads"
        description="Cadastros do popup, do formulário da home e de quem comprou. Base para campanhas de e-mail (via SMTP)."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => openCampaign(true)}>Criar campanha rápida</Button>
            <button
              type="button"
              onClick={exportCsv}
              className="rounded-btn border border-surface-border px-3 py-1.5 text-sm hover:border-primary"
            >
              Exportar CSV
            </button>
          </div>
        }
      />

      <AsyncBoundary loading={stats.loading} error={stats.error} onRetry={stats.reload}>
        {stats.data && (
          <div className="grid grid-cols-3 gap-3 sm:gap-4">
            {(
              [
                {
                  label: 'Leads pelo checkout',
                  value: formatNumber(stats.data.from_checkout),
                  key: 'checkout',
                },
                {
                  label: 'Leads pelo popup',
                  value: formatNumber(stats.data.from_popup),
                  key: 'popup',
                },
                {
                  label: 'Leads com cupom',
                  value: formatNumber(stats.data.from_coupon),
                  key: 'coupon',
                },
              ] as const
            ).map((c) => (
              <Card
                key={c.label}
                variant="elevated"
                as="button"
                onClick={() => applyQuick(c.key)}
                className={`flex w-full flex-col gap-1 text-left transition hover:border-primary ${
                  quick === c.key ? 'border-primary ring-1 ring-primary' : ''
                }`}
              >
                <span className="text-xs text-text-muted sm:text-sm">{c.label}</span>
                <span className="text-xl font-semibold sm:text-2xl">{c.value}</span>
              </Card>
            ))}
          </div>
        )}
      </AsyncBoundary>

      <Card variant="outline" className="flex flex-wrap items-end gap-3">
        <Select
          label="Origem"
          value={source}
          placeholder="Todas"
          options={sources.map((s) => ({ value: s, label: SOURCE_LABEL[s] ?? s }))}
          onChange={(e) => {
            setQuick('');
            setSource(e.target.value);
          }}
        />
        <span className="text-sm text-text-muted">{rows.length} lead(s)</span>
        {quick && (
          <button
            type="button"
            className="text-sm text-text-muted underline"
            onClick={() => setQuick('')}
          >
            limpar filtro dos cards
          </button>
        )}
      </Card>

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-card border border-surface-border bg-surface p-3">
          <span className="text-sm font-medium">{selected.size} selecionado(s)</span>
          <Button size="sm" onClick={() => openCampaign(false)}>
            Enviar campanha
          </Button>
          <Button size="sm" variant="ghost" className="text-danger" onClick={() => setConfirmDel(true)}>
            Excluir selecionados
          </Button>
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="text-sm text-text-muted underline"
          >
            Limpar seleção
          </button>
        </div>
      )}

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <div className="overflow-x-auto rounded-card border border-surface-border">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-bg-subtle text-left text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="w-10 px-3 py-2">
                  <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Selecionar todos" />
                </th>
                <th className="px-3 py-2">Nome</th>
                <th className="px-3 py-2">E-mail</th>
                <th className="px-3 py-2">Telefone</th>
                <th className="px-3 py-2">Origem</th>
                <th className="px-3 py-2">Cupom</th>
                <th className="px-3 py-2">Data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-text-muted">
                    Nenhum lead.
                  </td>
                </tr>
              )}
              {rows.map((l) => (
                <tr key={l.id} className={l.subscribed ? '' : 'opacity-50'}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(l.id)}
                      onChange={() => toggle(l.id)}
                      aria-label={`Selecionar ${l.email}`}
                    />
                  </td>
                  <td className="px-3 py-2">{l.name ?? '—'}</td>
                  <td className="px-3 py-2">{l.email}</td>
                  <td className="px-3 py-2">{l.phone ?? '—'}</td>
                  <td className="px-3 py-2">
                    <Badge tone="neutral">{SOURCE_LABEL[l.source] ?? l.source}</Badge>
                  </td>
                  <td className="px-3 py-2">{l.coupon_code ?? '—'}</td>
                  <td className="px-3 py-2 text-text-muted">
                    {l.created_at ? formatDateTime(l.created_at) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AsyncBoundary>

      <Modal
        open={campaignOpen}
        onClose={() => setCampaignOpen(false)}
        title={campaignAll ? 'Campanha rápida para toda a base' : 'Enviar campanha por e-mail'}
      >
        <div className="flex flex-col gap-3">
          <p className="text-sm text-text-muted">
            {campaignAll
              ? `Dispara para todos os ${campaignTargetCount} lead(s) inscrito(s), pelo SMTP configurado.`
              : `Envia para os ${campaignTargetCount} lead(s) selecionado(s), pelo SMTP configurado.`}
          </p>
          <Input label="Assunto" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <label className="flex flex-col gap-1 text-sm font-medium text-text">
            Conteúdo da promoção
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={6}
              className="rounded-card border border-surface-border bg-surface px-3 py-2 text-sm"
            />
            <span className="text-xs text-text-muted">
              Use <code>{'{nome}'}</code> para inserir o nome do lead.
            </span>
          </label>
          <Select
            label="Cupom (opcional)"
            value={couponCode}
            placeholder="Sem cupom"
            options={(coupons.data ?? []).map((c) => ({
              value: c.code,
              label: `${c.code} — ${c.description ?? c.type}`,
            }))}
            onChange={(e) => setCouponCode(e.target.value)}
          />
          <div className="flex gap-2">
            <Button loading={busy} onClick={() => void sendCampaign()}>
              Enviar
            </Button>
            <Button variant="outline" disabled={busy} onClick={() => setCampaignOpen(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={confirmDel}
        title="Excluir leads"
        description={`Excluir ${selected.size} lead(s)? Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir"
        tone="danger"
        loading={busy}
        onConfirm={() => void doDelete()}
        onCancel={() => setConfirmDel(false)}
      />
    </div>
  );
}
