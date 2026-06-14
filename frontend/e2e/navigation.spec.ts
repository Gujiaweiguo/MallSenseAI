import { expect, test } from '@playwright/test';

import { mockApi, mockLogin } from './helpers';

async function mockCommonPageData(page: import('@playwright/test').Page): Promise<void> {
  await mockApi(page, 'GET', '/dashboard/stats', {
    cameras_total: 1,
    cameras_active: 1,
    cameras_inactive: 0,
    cameras_error: 0,
    scenes_total: 1,
    alerts_total: 1,
    alerts_pending: 1,
    alerts_confirmed: 0,
    alerts_false_positive: 0,
    alerts_resolved: 0,
    alerts_by_severity: { low: 1 },
    work_orders_total: 1,
    work_orders_open: 1,
    work_orders_in_progress: 0,
    work_orders_closed: 0,
  });
  await mockApi(page, 'GET', '/alerts', []);
  await mockApi(page, 'GET', '/cameras', []);
  await mockApi(page, 'GET', '/scenes', []);
  await mockApi(page, 'GET', '/work-orders', []);
  await mockApi(page, 'GET', '/users', []);
}

test('admin can navigate through sidebar routes', async ({ page }) => {
  await mockLogin(page);
  await mockCommonPageData(page);

  await page.goto('/');
  await expect(page.getByRole('menuitem', { name: 'Dashboard' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Cameras' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Monitor Views' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Alerts' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Work Orders' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Users' })).toBeVisible();

  await page.getByRole('menuitem', { name: 'Cameras' }).click();
  await expect(page).toHaveURL('/cameras');
  await page.getByRole('menuitem', { name: 'Monitor Views' }).click();
  await expect(page).toHaveURL('/scenes');
  await page.getByRole('menuitem', { name: 'Alerts' }).click();
  await expect(page).toHaveURL('/alerts');
  await page.getByRole('menuitem', { name: 'Work Orders' }).click();
  await expect(page).toHaveURL('/work-orders');
  await page.getByRole('menuitem', { name: 'Users' }).click();
  await expect(page).toHaveURL('/users');
});

test('viewer does not see users menu and is redirected away from users route', async ({ page }) => {
  await mockLogin(page, {
    user: {
      id: 3,
      username: 'viewer',
      display_name: 'Viewer',
      role: 'viewer',
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  });
  await mockCommonPageData(page);

  await page.goto('/');
  await expect(page.getByRole('menuitem', { name: 'Users' })).toHaveCount(0);

  await page.goto('/users');
  await expect(page).toHaveURL('/');
});
