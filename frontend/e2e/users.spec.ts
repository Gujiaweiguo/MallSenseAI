import { expect, test } from '@playwright/test';

import { fulfillJson, mockLogin } from './helpers';

test('admin user management create, edit, and delete works', async ({ page }) => {
  await mockLogin(page);

  let users = [
    {
      id: 1,
      username: 'admin',
      display_name: 'Admin',
      role: 'admin',
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      username: 'viewer1',
      display_name: 'Viewer One',
      role: 'viewer',
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ];

  await page.route('**/api/users**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/users') {
      await fulfillJson(route, users);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/users') {
      const body = request.postDataJSON() as {
        username: string;
        display_name: string;
        role: string;
        enabled: boolean;
      };
      const created = {
        id: 3,
        username: body.username,
        display_name: body.display_name,
        role: body.role,
        enabled: body.enabled,
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      };
      users = [...users, created];
      await fulfillJson(route, created, 201);
      return;
    }

    await route.fallback();
  });

  await page.route('**/api/users/2', async (route) => {
    const request = route.request();
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as {
        username?: string;
        display_name?: string;
        role?: string;
        enabled?: boolean;
      };
      users = users.map((user) => (user.id === 2 ? { ...user, ...body } : user));
      await fulfillJson(route, users.find((user) => user.id === 2));
      return;
    }
    if (request.method() === 'DELETE') {
      users = users.filter((user) => user.id !== 2);
      await route.fulfill({ status: 204, body: '' });
      return;
    }
    await route.fallback();
  });

  await page.goto('/users');
  await expect(page.locator('.el-table')).toContainText('Admin');
  await expect(page.locator('.el-table')).toContainText('viewer1');

  await page.getByRole('button', { name: 'Add User' }).click();
  await page.getByRole('dialog').locator('input').nth(0).fill('operator2');
  await page.getByRole('dialog').locator('input').nth(1).fill('Operator Two');
  await page.getByRole('dialog').locator('input').nth(2).fill('password123');
  await page.getByRole('dialog').locator('.el-select').click();
  await page.getByText('Operator').click();
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.locator('.el-table')).toContainText('operator2');

  const viewerRow = page.locator('.el-table__row').filter({ hasText: 'viewer1' });
  await viewerRow.getByRole('button', { name: 'Edit' }).click();
  await page.getByRole('dialog').locator('input').nth(1).fill('Viewer Prime');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.locator('.el-table')).toContainText('Viewer Prime');

  await viewerRow.getByRole('button', { name: 'Delete' }).click();
  await page.locator('.el-popconfirm').getByRole('button', { name: 'Yes' }).click();
  await expect(page.locator('.el-table')).not.toContainText('viewer1');
});
