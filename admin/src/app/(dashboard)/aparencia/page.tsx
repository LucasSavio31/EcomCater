'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/page-header';
import { Tabs } from '@/components/tabs';
import { ThemeTab } from './_components/theme-tab';
import { BannersTab } from './_components/banners-tab';
import { PagesTab } from './_components/pages-tab';
import { StoreTab } from './_components/store-tab';

const TABS = [
  { id: 'tema', label: 'Cores e logo' },
  { id: 'banners', label: 'Banners' },
  { id: 'paginas', label: 'Páginas' },
  { id: 'loja', label: 'Dados da loja' },
];

export default function AparenciaPage() {
  const [tab, setTab] = useState('tema');
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Aparência" description="Identidade visual, banners, páginas e dados da loja." />
      <Tabs tabs={TABS} active={tab} onChange={setTab}>
        {tab === 'tema' && <ThemeTab />}
        {tab === 'banners' && <BannersTab />}
        {tab === 'paginas' && <PagesTab />}
        {tab === 'loja' && <StoreTab />}
      </Tabs>
    </div>
  );
}
