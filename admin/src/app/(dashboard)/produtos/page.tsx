import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Produtos' };

export default function ProdutosPage() {
  return <AdminStub title="Produtos" phase="Fase 2" />;
}
