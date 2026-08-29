import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Promoções' };

export default function PromocoesPage() {
  return <AdminStub title="Promoções" phase="Fase 5" />;
}
