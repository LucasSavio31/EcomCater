/** Tipos de `GET /api/menus/{header|footer}`. */

export interface SizeShortcut {
  label: string;
  url: string;
}

export interface MenuItem {
  id: string;
  label: string;
  url: string;
  highlight: boolean;
  is_megamenu: boolean;
  size_shortcuts: SizeShortcut[];
  children: MenuItem[];
}

export interface Menu {
  id: string;
  location: 'header' | 'footer';
  name: string;
  items: MenuItem[];
}
