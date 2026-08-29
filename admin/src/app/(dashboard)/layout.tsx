import { AdminAuthProvider } from '@/modules/auth';
import { AuthGuard } from '@/components/auth-guard';
import { AdminShell } from '@/components/admin-shell';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AuthGuard>
        <AdminShell>{children}</AdminShell>
      </AuthGuard>
    </AdminAuthProvider>
  );
}
