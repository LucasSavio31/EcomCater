import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'Menus' };

export default function MenusPage() {
  return <AdminStub title="Menus" phase="Fase 8" />;
}
