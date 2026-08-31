'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface SizeChart {
  id: string;
  name: string;
  columns: string[];
  rows: string[][];
  note: string | null;
}
export type SizeChartInput = Omit<SizeChart, 'id'>;

const BASE = '/api/admin/size_charts';

export const sizeChartsApi = {
  list: () => adminFetch<SizeChart[]>(BASE),
  create: (body: SizeChartInput) => adminFetch<SizeChart>(BASE, { method: 'POST', body }),
  update: (id: string, body: SizeChartInput) =>
    adminFetch<SizeChart>(`${BASE}/${id}`, { method: 'PATCH', body }),
  remove: (id: string) => adminFetch<void>(`${BASE}/${id}`, { method: 'DELETE' }),
};
