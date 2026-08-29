'use client';

import { adminFetch } from '@/lib/admin-api-client';

export type MenuLocation = 'header' | 'footer';
export type MenuLinkType = 'category' | 'url' | 'page';

export interface Menu {
  id: string;
  location: MenuLocation;
  name: string;
  position: number;
  is_active: boolean;
}

export interface MenuItem {
  id: string;
  menu_id: string;
  parent_id: string | null;
  label: string;
  link_type: MenuLinkType;
  category_id: string | null;
  url: string | null;
  position: number;
  is_megamenu: boolean;
  highlight: boolean;
  show_size_shortcuts: boolean;
  size_shortcut_category_id: string | null;
}

export interface MenuItemInput {
  label: string;
  link_type: MenuLinkType;
  category_id?: string | null;
  url?: string | null;
  position: number;
  parent_id?: string | null;
  is_megamenu?: boolean;
  highlight?: boolean;
  show_size_shortcuts?: boolean;
  size_shortcut_category_id?: string | null;
}

export interface ResolvedMenuItem extends MenuItem {
  children: ResolvedMenuItem[];
  resolved_url?: string | null;
}

export interface ResolvedMenu {
  location: MenuLocation;
  items: ResolvedMenuItem[];
}

export const menusApi = {
  list: () => adminFetch<Menu[]>('/api/admin/menus'),
  resolved: (location: MenuLocation) => adminFetch<ResolvedMenu>(`/api/admin/menus/${location}/resolved`),
  createMenu: (body: { location: MenuLocation; name: string; position: number; is_active: boolean }) =>
    adminFetch<Menu>('/api/admin/menus', { method: 'POST', body }),
  updateMenu: (id: string, body: Partial<{ name: string; position: number; is_active: boolean }>) =>
    adminFetch<Menu>(`/api/admin/menus/${id}`, { method: 'PATCH', body }),
  listItems: (menuId: string) => adminFetch<MenuItem[]>(`/api/admin/menus/${menuId}/items`),
  createItem: (menuId: string, body: MenuItemInput) =>
    adminFetch<MenuItem>(`/api/admin/menus/${menuId}/items`, { method: 'POST', body }),
  updateItem: (id: string, body: Partial<MenuItemInput>) =>
    adminFetch<MenuItem>(`/api/admin/menus/items/${id}`, { method: 'PATCH', body }),
  deleteItem: (id: string) => adminFetch<void>(`/api/admin/menus/items/${id}`, { method: 'DELETE' }),
  reorderItems: (items: Array<{ id: string; position: number; parent_id?: string | null }>) =>
    adminFetch<void>('/api/admin/menus/items/reorder', { method: 'POST', body: { items } }),
};
