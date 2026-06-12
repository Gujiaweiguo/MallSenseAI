import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getUser } from '@/api/resources';
import type { User, UserRole } from '@/api/types';

import { login as loginRequest } from './api';
import { AUTH_TOKEN_STORAGE_KEY, AUTH_USER_STORAGE_KEY } from './storage';
import type { AuthUser, LoginRequest } from './types';

interface JwtPayload {
  sub?: string;
  username?: string;
  display_name?: string;
  role?: UserRole;
}

function normalizeRole(value: unknown): UserRole | undefined {
  if (value === 'admin' || value === 'operator' || value === 'viewer') {
    return value;
  }
  return undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parseJwtPayload(tokenValue: string): JwtPayload | null {
  const payload = tokenValue.split('.')[1];
  if (payload === undefined) {
    return null;
  }

  try {
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=');
    const parsed = JSON.parse(window.atob(padded)) as unknown;
    if (!isRecord(parsed)) {
      return null;
    }
    return {
      sub: typeof parsed.sub === 'string' ? parsed.sub : undefined,
      username: typeof parsed.username === 'string' ? parsed.username : undefined,
      display_name: typeof parsed.display_name === 'string' ? parsed.display_name : undefined,
      role: normalizeRole(parsed.role),
    };
  } catch {
    return null;
  }
}

function toAuthUser(user: User): AuthUser {
  return {
    id: user.id,
    username: user.username,
    display_name: user.display_name,
    role: user.role,
  };
}

function isAuthUser(value: unknown): value is AuthUser {
  if (!isRecord(value)) {
    return false;
  }

  const hasValidId = value.id === undefined || typeof value.id === 'number';
  return (
    hasValidId &&
    typeof value.username === 'string' &&
    typeof value.display_name === 'string' &&
    normalizeRole(value.role) !== undefined
  );
}

function readStoredUser(): AuthUser | null {
  const stored = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (stored === null) {
    return null;
  }

  try {
    const parsed = JSON.parse(stored) as unknown;
    return isAuthUser(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

async function resolveCurrentUser(tokenValue: string, username: string): Promise<AuthUser> {
  const payload = parseJwtPayload(tokenValue);
  const userId = payload?.sub !== undefined ? Number(payload.sub) : Number.NaN;

  if (Number.isInteger(userId) && userId > 0) {
    try {
      return toAuthUser(await getUser(userId));
    } catch {
      // Fall through to token/login-derived display data when the user endpoint is unavailable.
    }
  }

  const resolvedUsername = payload?.username ?? username;
  return {
    username: resolvedUsername,
    display_name: payload?.display_name ?? resolvedUsername,
    role: payload?.role ?? (resolvedUsername === 'admin' ? 'admin' : 'viewer'),
  };
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY));
  const user = ref<AuthUser | null>(readStoredUser());

  const isAuthenticated = computed(() => token.value !== null && token.value.length > 0);
  const isAdmin = computed(() => user.value?.role === 'admin');

  function setSession(tokenValue: string, userValue: AuthUser): void {
    token.value = tokenValue;
    user.value = userValue;
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, tokenValue);
    window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(userValue));
  }

  function initializeFromStorage(): void {
    token.value = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    user.value = readStoredUser();
  }

  async function login(credentials: LoginRequest): Promise<void> {
    const tokenResponse = await loginRequest(credentials);
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, tokenResponse.access_token);
    const resolvedUser = await resolveCurrentUser(tokenResponse.access_token, credentials.username);
    setSession(tokenResponse.access_token, resolvedUser);
  }

  function logout(): void {
    token.value = null;
    user.value = null;
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    initializeFromStorage,
    login,
    logout,
  };
});
