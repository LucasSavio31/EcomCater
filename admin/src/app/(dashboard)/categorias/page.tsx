import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Categorias' };

export default function CategoriasPage() {
  return <AdminStub title="Categorias" phase="Fase 2" />;
}
