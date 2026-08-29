import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Usuários' };

export default function UsuariosPage() {
  return <AdminStub title="Usuários" phase="Fase 8" />;
}
