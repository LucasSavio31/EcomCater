/** DTOs do módulo `customers` (auth de cliente, perfil, endereços). */

export interface Customer {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  cpf: string | null;
}

export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Address {
  id: string;
  label: string;
  recipient_name: string;
  zip: string;
  street: string;
  number: string;
  complement: string | null;
  district: string;
  city: string;
  state: string;
  is_default: boolean;
}

export type AddressInput = Omit<Address, 'id'>;
