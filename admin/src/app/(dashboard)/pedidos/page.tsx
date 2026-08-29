import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Pedidos' };

export default function PedidosPage() {
  return <AdminStub title="Pedidos" phase="Fase 6" />;
}
