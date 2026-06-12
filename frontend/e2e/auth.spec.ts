import { expect, test } from '@playwright/test';

import { createFakeJwt, expectLoggedOut, mockApi } from './helpers';

test('auth guard redirects unauthenticated users to login', async ({ page }) => {
  await page.goto('/users');

  await expect(page).toHaveURL(/\/login\?redirect=\/users/);
  await expect(page.locator('input[placeholder="Username"]')).toBeVisible();
});

test('login, admin navigation, and logout work', async ({ page }) => {
  const token = createFakeJwt({ sub: '1' });

  await mockApi(page, 'POST', '/auth/login', { access_token: token, token_type: 'bearer' });
  await mockApi(page, 'GET', '/users/1', {
    id: 1,
    username: 'admin',
    display_name: 'Admin',
    role: 'admin',
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  });
  await mockApi(page, 'GET', '/dashboard/stats', {
    cameras_total: 0,
    cameras_active: 0,
    cameras_inactive: 0,
    cameras_error: 0,
    scenes_total: 0,
    alerts_total: 0,
    alerts_pending: 0,
    alerts_confirmed: 0,
    alerts_false_positive: 0,
    alerts_resolved: 0,
    alerts_by_severity: {},
    work_orders_total: 0,
    work_orders_open: 0,
    work_orders_in_progress: 0,
    work_orders_closed: 0,
  });
  await mockApi(page, 'GET', '/alerts', []);

  await page.goto('/login');

  await expect(page.locator('input[placeholder="Username"]')).toBeVisible();
  await expect(page.locator('input[placeholder="Password"]')).toBeVisible();
  await expect(page.locator('.login-view__submit')).toBeVisible();

  await page.locator('.login-view__submit').click();
  await expect(page.locator('.el-message')).toContainText('Username and password are required.');

  await page.locator('input[placeholder="Username"]').fill('admin');
  await page.locator('input[placeholder="Password"]').fill('admin123');
  await page.locator('.login-view__submit').click();

  await expect(page).toHaveURL('/');
  await expect(page.locator('.main-layout__title')).toHaveText('Dashboard');
  await expect(page.locator('.el-menu-item')).toContainText(['Dashboard', 'Cameras', 'Scenes', 'Alerts', 'Work Orders', 'Users']);

  await expect.poll(async () => page.evaluate(() => window.localStorage.getItem('mallsenseai.auth.token'))).toBe(token);
  await expect.poll(async () => page.evaluate(() => window.localStorage.getItem('mallsenseai.auth.user'))).not.toBeNull();

  await page.getByRole('button', { name: 'Logout' }).click();
  await expectLoggedOut(page);
});
