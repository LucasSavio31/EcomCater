'use client';

import Link from 'next/link';
import { useCallback, useState } from 'react';
import { Badge, Button, Input, Modal } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { PageSizeSelect, DEFAULT_PAGE_SIZE } from '@/components/date-range-filter';
import { Select, Textarea } from '@/components/form-controls';
import { ConfirmDialog, useConfirm } from '@/components/confirm-dialog';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatBRL, formatDateTime } from '@/lib/format';
import { nfeApi, nfeStatusLabel, nfeStatusTone, type NfeDocumentFull } from '@/modules/nfe/api';

const STATUS_OPTIONS = [
  { value: '', label: 'Todas' },
  { value: 'authorized', label: 'Autorizada' },
  { value: 'processing', label: 'Processando' },
  { value: 'pending', label: 'Pendente' },
  { value: 'rejected', label: 'Rejeitada' },
  { value: 'error', label: 'Erro' },
  { value: 'canceled', label: 'Cancelada' },
];

export default function NfeNotasPage() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const fetcher = useCallback(
    () => nfeApi.listDocuments({ page, pageSize, status: status || undefined }),
    [page, pageSize, status],
  );
  const { data, loading, error, reload, setData } = useResource(fetcher, [page, pageSize, status]);
  const rows = data?.items ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  const [detail, setDetail] = useState<NfeDocumentFull | null>(null);

  const [emailTarget, setEmailTarget] = useState<NfeDocumentFull | null>(null);
  const [emailTo, setEmailTo] = useState('');
  const [emailMini, setEmailMini] = useState(false);
  const [emailBusy, setEmailBusy] = useState(false);

  const [cancelTarget, setCancelTarget] = useState<NfeDocumentFull | null>(null);
  const [justificativa, setJustificativa] = useState('');
  const [cancelBusy, setCancelBusy] = useState(false);

  const del = useConfirm<NfeDocumentFull>();
  const [busyId, setBusyId] = useState<string | null>(null);

  function patchRow(doc: NfeDocumentFull): void {
    setData((prev) => (prev ? { ...prev, items: prev.items.map((i) => (i.id === doc.id ? doc : i)) } : prev));
    setDetail((d) => (d && d.id === doc.id ? doc : d));
  }

  async function doOpenDanfe(doc: NfeDocumentFull): Promise<void> {
    setBusyId(doc.id);
    const res = await nfeApi.openDocumentDanfe(doc.id);
    setBusyId(null);
    if (!res.ok) toast.error(res.message);
  }

  async function doOpenMiniDanfe(doc: NfeDocumentFull): Promise<void> {
    setBusyId(doc.id);
    const res = await nfeApi.openDocumentMiniDanfe(doc.id);
    setBusyId(null);
    if (!res.ok) toast.error(res.message);
  }

  async function doDownloadXml(doc: NfeDocumentFull): Promise<void> {
    setBusyId(doc.id);
    const res = await nfeApi.downloadDocumentXml(doc.id);
    setBusyId(null);
    if (!res.ok) toast.error(res.message);
  }

  function openEmail(doc: NfeDocumentFull): void {
    setEmailTarget(doc);
    setEmailTo('');
    setEmailMini(false);
  }

  async function sendEmail(): Promise<void> {
    if (!emailTarget) return;
    if (!emailTo.trim()) {
      toast.error('Informe o e-mail de destino.');
      return;
    }
    setEmailBusy(true);
    const res = await nfeApi.emailDocument(emailTarget.id, emailTo.trim(), emailMini);
    setEmailBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('E-mail enviado.');
    setEmailTarget(null);
  }

  function openCancel(doc: NfeDocumentFull): void {
    setCancelTarget(doc);
    setJustificativa('');
  }

  async function doCancel(): Promise<void> {
    if (!cancelTarget) return;
    if (justificativa.trim().length < 15) {
      toast.error('Justificativa precisa ter pelo menos 15 caracteres.');
      return;
    }
    setCancelBusy(true);
    const res = await nfeApi.cancelDocument(cancelTarget.id, justificativa.trim());
    setCancelBusy(false);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('NF-e cancelada.');
    patchRow(res.data);
    setCancelTarget(null);
  }

  async function doDelete(doc: NfeDocumentFull): Promise<void> {
    const res = await nfeApi.deleteDocument(doc.id);
    if (!res.ok) {
      toast.error(res.error.message);
      return;
    }
    toast.success('Excluída.');
    setData((prev) => (prev ? { ...prev, items: prev.items.filter((i) => i.id !== doc.id), total: prev.total - 1 } : prev));
  }

  const columns: Array<Column<NfeDocumentFull>> = [
    {
      key: 'numero',
      header: 'Número/Série',
      cell: (d) => (d.numero ? `${d.numero}/${d.serie ?? '—'}` : '—'),
      primary: true,
    },
    { key: 'pedido', header: 'Pedido', cell: (d) => d.order_number },
    { key: 'dest', header: 'Destinatário', cell: (d) => d.destinatario_nome || '—' },
    { key: 'data', header: 'Data', cell: (d) => formatDateTime(d.authorized_at ?? d.requested_at ?? d.created_at) },
    { key: 'valor', header: 'Valor', cell: (d) => formatBRL(d.total_cents) },
    {
      key: 'status',
      header: 'Status',
      cell: (d) => (
        <div className="flex flex-col gap-0.5">
          <Badge tone={nfeStatusTone(d.status)}>{nfeStatusLabel(d.status)}</Badge>
          {(d.status === 'rejected' || d.status === 'error') && d.status_message && (
            <span className="text-xs text-danger">{d.status_message}</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Notas emitidas"
        description="Todas as NF-e emitidas, com paginação e busca por status."
        actions={
          <Link href="/nfe" className="text-sm text-accent hover:underline">
            → Configuração de emissão
          </Link>
        }
      />

      <div className="max-w-xs">
        <Select
          label="Status"
          value={status}
          options={STATUS_OPTIONS}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        />
      </div>

      <DataTable
        tableId="nfe-notas"
        columns={columns}
        rows={rows}
        rowKey={(d) => d.id}
        loading={loading}
        error={error}
        emptyMessage="Nenhuma NF-e encontrada."
        onRowClick={(d) => setDetail(d)}
        rowActions={(d) => {
          const chip =
            'inline-flex items-center gap-1 rounded-card border border-surface-border px-2 py-1 text-xs hover:border-primary disabled:opacity-50';
          const canDelete = d.status !== 'authorized' && d.status !== 'canceled';
          return (
            <>
              {d.status === 'authorized' && (
                <>
                  <button
                    type="button"
                    disabled={busyId === d.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      void doOpenDanfe(d);
                    }}
                    className={chip}
                  >
                    DANFE A4
                  </button>
                  <button
                    type="button"
                    disabled={busyId === d.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      void doOpenMiniDanfe(d);
                    }}
                    className={chip}
                  >
                    NFCe simplificada
                  </button>
                  <button
                    type="button"
                    disabled={busyId === d.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      void doDownloadXml(d);
                    }}
                    className={chip}
                  >
                    XML
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEmail(d);
                    }}
                    className={chip}
                  >
                    E-mail
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openCancel(d);
                    }}
                    className={`${chip} text-danger hover:border-danger`}
                  >
                    Cancelar
                  </button>
                </>
              )}
              {canDelete && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    del.ask(d);
                  }}
                  className={`${chip} text-danger hover:border-danger`}
                >
                  Excluir
                </button>
              )}
            </>
          );
        }}
      />

      {data && data.total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-4">
            <span className="text-text-muted">
              {data.total} {data.total === 1 ? 'nota' : 'notas'}
            </span>
            <PageSizeSelect
              value={pageSize}
              onChange={(n) => {
                setPage(1);
                setPageSize(n);
              }}
            />
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </Button>
              <span>
                Página {page} de {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </Button>
            </div>
          )}
        </div>
      )}

      {error && (
        <button type="button" onClick={reload} className="self-start text-sm text-accent hover:underline">
          Recarregar
        </button>
      )}

      {/* --------------------------------------------------------- detalhe */}
      <Modal open={detail !== null} onClose={() => setDetail(null)} title="Detalhes da NF-e" size="md">
        {detail && (
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex items-center gap-2">
              <Badge tone={nfeStatusTone(detail.status)}>{nfeStatusLabel(detail.status)}</Badge>
              {(detail.status === 'rejected' || detail.status === 'error') && detail.status_message && (
                <span className="text-danger">{detail.status_message}</span>
              )}
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
              <dt className="text-text-muted">Pedido</dt>
              <dd>{detail.order_number}</dd>
              <dt className="text-text-muted">Número/Série</dt>
              <dd>{detail.numero ? `${detail.numero}/${detail.serie ?? '—'}` : '—'}</dd>
              <dt className="text-text-muted">Destinatário</dt>
              <dd>{detail.destinatario_nome || '—'}</dd>
              <dt className="text-text-muted">Natureza da operação</dt>
              <dd>{detail.natureza_operacao || '—'}</dd>
              <dt className="text-text-muted">Valor</dt>
              <dd>{formatBRL(detail.total_cents)}</dd>
              <dt className="text-text-muted">Ambiente</dt>
              <dd>{detail.ambiente === 'producao' ? 'Produção' : 'Homologação'}</dd>
              <dt className="text-text-muted">Chave de acesso</dt>
              <dd className="col-span-1 break-all font-mono text-xs">{detail.chave_acesso || '—'}</dd>
              <dt className="text-text-muted">Protocolo</dt>
              <dd>{detail.protocolo_autorizacao || '—'}</dd>
              <dt className="text-text-muted">Solicitada em</dt>
              <dd>{formatDateTime(detail.requested_at)}</dd>
              <dt className="text-text-muted">Autorizada em</dt>
              <dd>{formatDateTime(detail.authorized_at)}</dd>
              {detail.status === 'canceled' && (
                <>
                  <dt className="text-text-muted">Cancelada em</dt>
                  <dd>{formatDateTime(detail.canceled_at)}</dd>
                  <dt className="text-text-muted">Justificativa</dt>
                  <dd className="col-span-1">{detail.cancel_justificativa || '—'}</dd>
                </>
              )}
            </dl>
          </div>
        )}
      </Modal>

      {/* --------------------------------------------------------- e-mail */}
      <Modal
        open={emailTarget !== null}
        onClose={() => setEmailTarget(null)}
        title="Enviar NF-e por e-mail"
        footer={
          <>
            <Button variant="ghost" onClick={() => setEmailTarget(null)} disabled={emailBusy}>
              Cancelar
            </Button>
            <Button onClick={() => void sendEmail()} loading={emailBusy}>
              Enviar
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <Input
            label="E-mail de destino"
            type="email"
            placeholder="contador@empresa.com.br"
            value={emailTo}
            onChange={(e) => setEmailTo(e.target.value)}
          />
          <Select
            label="Formato anexado"
            value={emailMini ? 'mini' : 'a4'}
            options={[
              { value: 'a4', label: 'DANFE A4' },
              { value: 'mini', label: 'NFCe simplificada (10x15)' },
            ]}
            onChange={(e) => setEmailMini(e.target.value === 'mini')}
          />
        </div>
      </Modal>

      {/* --------------------------------------------------------- cancelamento */}
      <Modal
        open={cancelTarget !== null}
        onClose={() => setCancelTarget(null)}
        title="Cancelar NF-e"
        description="A SEFAZ exige uma justificativa com pelo menos 15 caracteres. Só é possível cancelar dentro do prazo legal (normalmente 24h após a autorização)."
        footer={
          <>
            <Button variant="ghost" onClick={() => setCancelTarget(null)} disabled={cancelBusy}>
              Voltar
            </Button>
            <Button variant="danger" onClick={() => void doCancel()} loading={cancelBusy}>
              Cancelar nota
            </Button>
          </>
        }
      >
        <Textarea label="Justificativa" value={justificativa} onChange={(e) => setJustificativa(e.target.value)} rows={3} />
      </Modal>

      {/* --------------------------------------------------------- exclusão */}
      <ConfirmDialog
        open={del.open}
        title="Excluir NF-e"
        description="Só é possível excluir tentativas que nunca chegaram a ser autorizadas (pendente, processando, rejeitada ou erro). Notas autorizadas ou canceladas são documento fiscal e ficam guardadas."
        tone="danger"
        confirmLabel="Excluir"
        loading={del.loading}
        onCancel={del.cancel}
        onConfirm={() => void del.run(doDelete)}
      />
    </div>
  );
}
