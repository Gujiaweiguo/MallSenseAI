import { expect, type Page, type Route } from '@playwright/test';

export interface MockUser {
  id: number;
  username: string;
  display_name: string;
  role: 'admin' | 'operator' | 'viewer';
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export function createFakeJwt(payload: { sub: string; exp?: number }): string {
  const header = { alg: 'HS256', typ: 'JWT' };
  const body = { exp: 4_102_444_800, ...payload };

  return [header, body, 'signature']
    .map((part) => {
      const value = typeof part === 'string' ? part : JSON.stringify(part);
      return Buffer.from(value).toString('base64url');
    })
    .join('.');
}

function normalizePath(path: string): string {
  return path.startsWith('/api') ? path : `/api${path}`;
}

function matchesPath(requestUrl: string, path: string): boolean {
  const url = new URL(requestUrl);
  const normalizedPath = normalizePath(path);
  return url.pathname === normalizedPath;
}

export async function mockApi<T>(
  page: Page,
  method: string,
  path: string,
  response: T,
  status = 200,
): Promise<void> {
  const upperMethod = method.toUpperCase();

  await page.route(`**${normalizePath(path)}*`, async (route) => {
    if (route.request().method() !== upperMethod || !matchesPath(route.request().url(), path)) {
      await route.fallback();
      return;
    }

    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

export async function mockLogin(
  page: Page,
  options?: {
    user?: MockUser;
  },
): Promise<MockUser> {
  const user: MockUser = options?.user ?? {
    id: 1,
    username: 'admin',
    display_name: 'Admin',
    role: 'admin',
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
  const token = createFakeJwt({ sub: String(user.id) });

  await page.addInitScript(
    ({ authToken, authUser, tokenStorageKey, userStorageKey, localeKey, localeVal }) => {
      window.localStorage.setItem(tokenStorageKey, authToken);
      window.localStorage.setItem(userStorageKey, JSON.stringify(authUser));
      window.localStorage.setItem(localeKey, localeVal);
    },
    {
      authToken: token,
      authUser: { id: user.id, username: user.username, display_name: user.display_name, role: user.role },
      tokenStorageKey: 'mallsenseai.auth.token',
      userStorageKey: 'mallsenseai.auth.user',
      localeKey: 'mallsenseai.locale',
      localeVal: 'en',
    },
  );

  await mockApi(page, 'GET', `/users/${user.id}`, user);
  await mockApi(page, 'POST', '/auth/login', { access_token: token, token_type: 'bearer' });

  return user;
}

export async function expectLoggedOut(page: Page): Promise<void> {
  await expect(page).toHaveURL(/\/login/);
  await expect.poll(async () => page.evaluate(() => window.localStorage.getItem('mallsenseai.auth.token'))).toBeNull();
}

export async function fulfillJson(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}
