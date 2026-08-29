'use client';

import { useId } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@ecom/ui';

export interface TabDef {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
  children: ReactNode;
}

/** Barra de abas acessível (role=tablist) com painel único controlado pelo pai. */
export function Tabs({ tabs, active, onChange, children }: TabsProps) {
  const baseId = useId();
  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label="Seções"
        className="flex flex-wrap gap-1 overflow-x-auto rounded-card border border-surface-border bg-bg-subtle p-1"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`${baseId}-${tab.id}-tab`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel`}
              onClick={() => onChange(tab.id)}
              className={cn(
                'min-h-touch whitespace-nowrap rounded-card px-3 text-sm font-medium transition',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                selected ? 'bg-surface text-text shadow-sm' : 'text-text-muted hover:text-text',
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`${baseId}-panel`}>
        {children}
      </div>
    </div>
  );
}
