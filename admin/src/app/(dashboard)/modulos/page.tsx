import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Módulos' };

export default function ModulosPage() {
  return <AdminStub title="Módulos" phase="Fase 5 / Fase 7" />;
}
