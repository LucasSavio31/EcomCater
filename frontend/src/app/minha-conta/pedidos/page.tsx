'use client';

import Link from 'next/link';
import { AccountGate } from '@/components/account/account-gate';
import { OrdersList } from '@/components/account/orders-list';

export default function MeusPedidosPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold sm:text-2xl">Meus pedidos</h1>
        <Link href="/minha-conta" className="text-sm text-primary underline">
          ← Minha conta
        </Link>
      </div>
      <AccountGate intro="Entre na sua conta para ver seus pedidos.">
        <OrdersList />
      </AccountGate>
    </div>
  );
}
