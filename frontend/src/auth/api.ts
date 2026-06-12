import client from '@/api/client';

import type { LoginRequest, TokenResponse } from './types';

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await client.post<TokenResponse>('/auth/login', payload);
  return response.data;
}
