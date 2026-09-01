'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/page-header';
import { Tabs } from '@/components/tabs';
import { ColorsTab } from './_components/colors-tab';
import { HeaderFooterTab } from './_components/header-footer-tab';
import { ProductPageTab } from './_components/product-page-tab';
import { CartTab } from './_components/cart-tab';
import { PopupsTab } from './_components/popups-tab';
import { EmailsTab } from './_components/emails-tab';
import { BannersTab } from './_components/banners-tab';
import { PagesTab } from './_components/pages-tab';
import { StoreTab } from './_components/store-tab';

const TABS = [
  { id: 'cores', label: 'Cores gerais' },
  { id: 'cabecalho', label: 'Cabeçalho e rodapé' },
  { id: 'produto', label: 'Página de produto' },
  { id: 'carrinho', label: 'Carrinho' },
  { id: 'popups', label: 'Popups' },
  { id: 'emails', label: 'E-mails' },
  { id: 'banners', label: 'Banners' },
  { id: 'paginas', label: 'Páginas' },
  { id: 'loja', label: 'Dados da loja' },
];

export default function AparenciaPage() {
  const [tab, setTab] = useState('cores');
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Aparência"
        description="Identidade visual da loja, organizada por área."
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab}>
        {tab === 'cores' && <ColorsTab />}
        {tab === 'cabecalho' && <HeaderFooterTab />}
        {tab === 'produto' && <ProductPageTab />}
        {tab === 'carrinho' && <CartTab />}
        {tab === 'popups' && <PopupsTab />}
        {tab === 'emails' && <EmailsTab />}
        {tab === 'banners' && <BannersTab />}
        {tab === 'paginas' && <PagesTab />}
        {tab === 'loja' && <StoreTab />}
      </Tabs>
    </div>
  );
}
