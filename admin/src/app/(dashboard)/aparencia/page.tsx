import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Aparência' };

export default function AparenciaPage() {
  return <AdminStub title="Aparência" phase="Fase 8" />;
}
