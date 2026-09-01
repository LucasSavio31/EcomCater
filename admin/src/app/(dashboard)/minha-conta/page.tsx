'use client';

import { PageHeader } from '@/components/page-header';
import { AccountTab } from './_components/account-tab';

export default function MinhaContaPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Minha conta"
        description="Seus dados de acesso e a segurança da conta."
      />
      <AccountTab />
    </div>
  );
}
