'use client';

import { adminFetch } from '@/lib/admin-api-client';

export interface LiveVisitor {
  country: string | null;
  country_code: string | null;
  region: string | null;
  city: string | null;
  lat: number | null;
  lon: number | null;
  path: string;
  page_label: string;
  ip: string | null;
  device: string | null;
  since_seconds: number;
}

export interface LiveVisitorsData {
  total: number;
  visitors: LiveVisitor[];
  top_states: { region: string; count: number }[];
}

export const presenceApi = {
  live: () => adminFetch<LiveVisitorsData>('/api/admin/presence/live'),
};
