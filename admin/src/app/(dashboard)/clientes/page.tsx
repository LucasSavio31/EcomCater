import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Clientes' };

export default function ClientesPage() {
  return <AdminStub title="Clientes" phase="Fase 8" />;
}
