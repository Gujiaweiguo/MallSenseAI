import { expect, test } from '@playwright/test';

import { fulfillJson, mockLogin } from './helpers';

test('alerts list, actions, and filtering work', async ({ page }) => {
  await mockLogin(page);

  let alerts = [
    {
      id: 1,
      camera_id: 1,
      roi_id: null,
      rule_id: null,
      alert_type: 'obstruction',
      severity: 'critical',
      status: 'pending',
      evidence_image_path: null,
      detected_at: '2026-01-01T01:00:00Z',
      resolved_at: null,
      event_metadata: {},
      created_at: '2026-01-01T01:00:00Z',
      updated_at: '2026-01-01T01:00:00Z',
    },
    {
      id: 2,
      camera_id: 2,
      roi_id: null,
      rule_id: null,
      alert_type: 'object_count',
      severity: 'low',
      status: 'resolved',
      evidence_image_path: null,
      detected_at: '2026-01-01T02:00:00Z',
      resolved_at: '2026-01-01T03:00:00Z',
      event_metadata: {},
      created_at: '2026-01-01T02:00:00Z',
      updated_at: '2026-01-01T03:00:00Z',
    },
  ];

  await page.route('**/api/alerts**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/alerts') {
      await fulfillJson(route, alerts);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/alerts/1/confirm') {
      alerts = alerts.map((alert) => (alert.id === 1 ? { ...alert, status: 'confirmed' } : alert));
      await fulfillJson(route, alerts[0]);
      return;
    }

    await route.fallback();
  });

  await page.goto('/alerts');
  await expect(page.locator('.el-table')).toContainText('obstruction');
  await expect(page.locator('.el-table')).toContainText('critical');
  await expect(page.locator('.el-table')).toContainText('pending');
  await expect(page.locator('.el-table')).toContainText('object_count');
  await expect(page.locator('.el-table')).toContainText('resolved');

  await page.getByRole('button', { name: 'Confirm' }).click();
  await expect(page.locator('.el-table')).toContainText('confirmed');

  await page.locator('.filter-bar .el-select').first().click();
  await page.locator('.el-select-dropdown:visible').getByText('Critical', { exact: true }).click();
  await expect(page.locator('.el-table')).toContainText('obstruction');
  await expect(page.locator('.el-table')).not.toContainText('object_count');
});
