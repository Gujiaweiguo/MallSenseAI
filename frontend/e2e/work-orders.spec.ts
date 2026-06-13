import { expect, test } from '@playwright/test';

import { fulfillJson, mockLogin } from './helpers';

test('work-order list and status transitions work', async ({ page }) => {
  await mockLogin(page);

  let workOrders = [
    {
      id: 1,
      alert_id: 10,
      assigned_to: null,
      status: 'open',
      notes: 'Needs inspection',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      alert_id: 11,
      assigned_to: 2,
      status: 'closed',
      notes: 'Completed',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ];

  await page.route('**/api/work-orders**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/work-orders') {
      await fulfillJson(route, workOrders);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/work-orders/1/transition') {
      const body = request.postDataJSON() as { target: string };
      workOrders = workOrders.map((order) => (order.id === 1 ? { ...order, status: body.target } : order));
      await fulfillJson(route, workOrders[0]);
      return;
    }

    await route.fallback();
  });

  await page.route('**/api/users*', async (route) => {
    if (route.request().method() === 'GET') {
      await fulfillJson(route, [
        {
          id: 2,
          username: 'operator1',
          display_name: 'Operator One',
          role: 'operator',
          enabled: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]);
      return;
    }
    await route.fallback();
  });

  await page.goto('/work-orders');
  await expect(page.locator('.el-table')).toContainText('Needs inspection');
  await expect(page.locator('.el-table')).toContainText('Open');
  await expect(page.locator('.el-table')).toContainText('Completed');
  await expect(page.locator('.el-table')).toContainText('Closed');

  await page.getByRole('button', { name: 'Start' }).click();
  await expect(page.locator('.el-table')).toContainText('In Progress');
});
