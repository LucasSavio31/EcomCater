import { AdminAuthProvider } from '@/modules/auth';
import { AuthGuard } from '@/components/auth-guard';
import { AdminShell } from '@/components/admin-shell';
import { ToastProvider } from '@/components/toast';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AuthGuard>
        <ToastProvider>
          <AdminShell>{children}</AdminShell>
        </ToastProvider>
      </AuthGuard>
    </AdminAuthProvider>
  );
}
