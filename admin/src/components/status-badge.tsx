import { Badge } from '@ecom/ui';
import type { BadgeTone } from '@ecom/ui';

const ORDER_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  pending_payment: { label: 'Aguardando pagamento', tone: 'warning' },
  paid: { label: 'Pago', tone: 'success' },
  processing: { label: 'Em separação', tone: 'accent' },
  shipped: { label: 'Enviado', tone: 'accent' },
  delivered: { label: 'Entregue', tone: 'success' },
  canceled: { label: 'Cancelado', tone: 'neutral' },
  refunded: { label: 'Reembolsado', tone: 'danger' },
};

const PAYMENT_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  pending: { label: 'Pendente', tone: 'warning' },
  authorized: { label: 'Autorizado', tone: 'accent' },
  paid: { label: 'Pago', tone: 'success' },
  failed: { label: 'Falhou', tone: 'danger' },
  refunded: { label: 'Reembolsado', tone: 'danger' },
  chargeback: { label: 'Chargeback', tone: 'danger' },
};

const PRODUCT_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  draft: { label: 'Rascunho', tone: 'neutral' },
  active: { label: 'Ativo', tone: 'success' },
  archived: { label: 'Arquivado', tone: 'warning' },
};

const REVIEW_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  pending: { label: 'Pendente', tone: 'warning' },
  approved: { label: 'Aprovada', tone: 'success' },
  rejected: { label: 'Rejeitada', tone: 'danger' },
};

type Kind = 'order' | 'payment' | 'product' | 'review';

const MAPS: Record<Kind, Record<string, { label: string; tone: BadgeTone }>> = {
  order: ORDER_STATUS,
  payment: PAYMENT_STATUS,
  product: PRODUCT_STATUS,
  review: REVIEW_STATUS,
};

export function StatusBadge({ kind, value }: { kind: Kind; value: string }) {
  const entry = MAPS[kind][value];
  if (!entry) return <Badge tone="neutral">{value}</Badge>;
  return <Badge tone={entry.tone}>{entry.label}</Badge>;
}

export function orderStatusLabel(value: string): string {
  return ORDER_STATUS[value]?.label ?? value;
}
