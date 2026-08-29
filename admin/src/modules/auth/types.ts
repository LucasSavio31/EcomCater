/** DTOs de auth do admin (espelham `api/app/modules/admin/schemas.py`). */

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type AdminRole = 'super_admin' | 'admin' | 'staff';

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: AdminRole;
  must_change_password: boolean;
  is_active: boolean;
  last_login_at: string | null;
}
