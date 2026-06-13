import { expect, test } from '@playwright/test';

import { fulfillJson, mockLogin } from './helpers';

test('camera list, detail, create, and delete flows work', async ({ page }) => {
  await mockLogin(page);

  let cameras = [
    {
      id: 1,
      name: 'Entrance Cam',
      location: 'North Gate',
      ip: '192.168.1.10',
      port: 80,
      status: 'active',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      username: 'admin',
    },
    {
      id: 2,
      name: 'Corridor Cam',
      location: '1F East Corridor',
      ip: '192.168.1.11',
      port: 80,
      status: 'inactive',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      username: 'admin',
    },
  ];

  await page.route('**/api/cameras*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/cameras') {
      await fulfillJson(route, cameras);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/cameras') {
      const body = request.postDataJSON() as {
        name: string;
        location: string;
        ip: string;
        port: number;
        username: string;
        password: string;
        status: string;
      };
      cameras = [
        ...cameras,
        {
          id: 3,
          name: body.name,
          location: body.location,
          ip: body.ip,
          port: body.port,
          status: body.status,
          created_at: '2026-01-02T00:00:00Z',
          updated_at: '2026-01-02T00:00:00Z',
          username: body.username,
        },
      ];
      await fulfillJson(route, cameras[cameras.length - 1], 201);
      return;
    }

    await route.fallback();
  });

  await page.route('**/api/cameras/1', async (route) => {
    if (route.request().method() === 'GET') {
      await fulfillJson(route, cameras[0]);
      return;
    }
    await route.fallback();
  });

  await page.route('**/api/cameras/2', async (route) => {
    if (route.request().method() === 'DELETE') {
      cameras = cameras.filter((camera) => camera.id !== 2);
      await route.fulfill({ status: 204, body: '' });
      return;
    }
    await route.fallback();
  });

  await page.goto('/cameras');

  await expect(page.locator('.el-table')).toContainText('Entrance Cam');
  await expect(page.locator('.el-table')).toContainText('192.168.1.10');
    await expect(page.locator('.el-table')).toContainText('Active');
  await expect(page.locator('.el-table')).toContainText('Corridor Cam');
  await expect(page.locator('.el-table')).toContainText('192.168.1.11');
    await expect(page.locator('.el-table')).toContainText('Inactive');

  await page.getByRole('link', { name: 'Entrance Cam' }).click();
  await expect(page).toHaveURL('/cameras/1');
  await expect(page.locator('.el-descriptions')).toContainText('Entrance Cam');
  await expect(page.locator('.el-descriptions')).toContainText('North Gate');
  await expect(page.locator('.el-descriptions')).toContainText('192.168.1.10');

  await page.goto('/cameras');
  await page.getByRole('button', { name: 'Add Camera' }).click();
  await expect(page.getByRole('dialog')).toContainText('Add Camera');
  await page.locator('input[placeholder="Camera name"]').fill('Loading Dock Cam');
  await page.locator('input[placeholder="e.g. 1F East Corridor"]').fill('Loading Dock');
  await page.locator('input[placeholder="192.168.1.100"]').fill('192.168.1.12');
  await page.locator('input[placeholder="Camera HTTP auth username"]').fill('dock-admin');
  await page.locator('input[placeholder="Camera HTTP auth password"]').fill('secret123');
  await page.getByRole('button', { name: 'Create' }).click();
  await expect(page.locator('.el-table')).toContainText('Loading Dock Cam');

  const row = page.locator('.el-table__row').filter({ hasText: 'Corridor Cam' });
  await row.getByRole('button', { name: 'Delete' }).click();
  await page.locator('.el-popconfirm').getByRole('button', { name: 'Delete' }).click();
  await expect(page.locator('.el-table')).not.toContainText('Corridor Cam');
});
