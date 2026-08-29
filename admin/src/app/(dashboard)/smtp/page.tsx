import type { Metadata } from 'next';
import { AdminStub } from '@/components/admin-stub';

export const metadata: Metadata = { title: 'SMTP' };

export default function SmtpPage() {
  return <AdminStub title="SMTP" phase="Fase 7" />;
}
