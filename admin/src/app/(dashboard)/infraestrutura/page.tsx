'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/page-header';
import { Tabs, type TabDef } from '@/components/tabs';
import { HealthTab } from './_components/health-tab';
import { BackupTab } from './_components/backup-tab';

const TABS: TabDef[] = [
  { id: 'saude', label: 'Saúde dos serviços' },
  { id: 'backup', label: 'Backup' },
];

export default function InfraestruturaPage() {
  const [tab, setTab] = useState('saude');

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Infraestrutura"
        description="Saúde dos serviços e containers em tempo real e os backups completos do sistema."
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab}>
        {tab === 'saude' && <HealthTab />}
        {tab === 'backup' && <BackupTab />}
      </Tabs>
    </div>
  );
}
