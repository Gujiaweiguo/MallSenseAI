import type { UserRole } from '@/api/types';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer' | string;
}

export interface AuthUser {
  id?: number;
  username: string;
  display_name: string;
  role: UserRole;
}
