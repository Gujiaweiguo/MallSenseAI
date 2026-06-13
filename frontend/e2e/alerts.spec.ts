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
      alert_type: 'obstruction_duration',
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
      alert_type: 'fire_smoke',
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

  await page.route('**/api/cameras**', async (route) => {
    if (route.request().method() === 'GET' && new URL(route.request().url()).pathname === '/api/cameras') {
      await fulfillJson(route, [
        { id: 1, name: 'Cam 1', location: 'Floor 1', ip: '10.0.0.1', port: 80, status: 'active', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
        { id: 2, name: 'Cam 2', location: 'Floor 2', ip: '10.0.0.2', port: 80, status: 'active', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
      ]);
      return;
    }
    await route.fallback();
  });

  await page.goto('/alerts');
  await expect(page.locator('.el-table')).toContainText('obstruction_duration');
  await expect(page.locator('.el-table')).toContainText('critical');
  await expect(page.locator('.el-table')).toContainText('pending');
  await expect(page.locator('.el-table')).toContainText('fire_smoke');
  await expect(page.locator('.el-table')).toContainText('resolved');
  await expect(page.locator('.el-table')).toContainText('Cam 1');
  await expect(page.locator('.el-table')).toContainText('Cam 2');

  await page.getByRole('button', { name: 'Confirm' }).click();
  await expect(page.locator('.el-table')).toContainText('confirmed');

  await page.locator('.filter-bar .el-select').first().click();
  await page.locator('.el-select-dropdown:visible').getByText('Critical', { exact: true }).click();
  await expect(page.locator('.el-table')).toContainText('obstruction_duration');
  await expect(page.locator('.el-table')).not.toContainText('fire_smoke');
});

test('batch confirm confirms multiple selected alerts', async ({ page }) => {
  await mockLogin(page);

  let alerts = [
    {
      id: 10,
      camera_id: 1,
      roi_id: null,
      rule_id: null,
      alert_type: 'obstruction_area',
      severity: 'high',
      status: 'pending',
      evidence_image_path: null,
      detected_at: '2026-01-01T01:00:00Z',
      resolved_at: null,
      event_metadata: {},
      created_at: '2026-01-01T01:00:00Z',
      updated_at: '2026-01-01T01:00:00Z',
    },
    {
      id: 11,
      camera_id: 1,
      roi_id: null,
      rule_id: null,
      alert_type: 'litter',
      severity: 'medium',
      status: 'pending',
      evidence_image_path: null,
      detected_at: '2026-01-01T02:00:00Z',
      resolved_at: null,
      event_metadata: {},
      created_at: '2026-01-01T02:00:00Z',
      updated_at: '2026-01-01T02:00:00Z',
    },
  ];

  await page.route('**/api/alerts**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/alerts') {
      await fulfillJson(route, alerts);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/alerts/batch') {
      const body = request.postDataJSON();
      alerts = alerts.map((a) => (body.alert_ids.includes(a.id) ? { ...a, status: 'confirmed' } : a));
      await fulfillJson(route, { processed: body.alert_ids.length, failed: [] });
      return;
    }

    await route.fallback();
  });

  await page.route('**/api/cameras**', async (route) => {
    if (route.request().method() === 'GET' && new URL(route.request().url()).pathname === '/api/cameras') {
      await fulfillJson(route, [
        { id: 1, name: 'Cam 1', location: 'Floor 1', ip: '10.0.0.1', port: 80, status: 'active', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
      ]);
      return;
    }
    await route.fallback();
  });

  await page.goto('/alerts');
  await expect(page.locator('.el-table')).toContainText('pending');

  const rowCheckboxes = page.locator('.el-table__body-wrapper .el-checkbox');
  await rowCheckboxes.nth(0).click();
  await rowCheckboxes.nth(1).click();

  await expect(page.locator('.batch-bar')).toBeVisible();
  await expect(page.locator('.batch-bar')).toContainText('2 selected');

  await page.getByRole('button', { name: 'Batch Confirm' }).click();
  await page.locator('.el-message-box').getByRole('button', { name: 'Confirm' }).click();

  await expect(page.locator('.el-table')).toContainText('confirmed');
  await expect(page.locator('.batch-bar')).not.toBeVisible();
});

test('batch bar clear button deselects all rows', async ({ page }) => {
  await mockLogin(page);

  const alerts = [
    {
      id: 20,
      camera_id: 1,
      roi_id: null,
      rule_id: null,
      alert_type: 'obstruction_duration',
      severity: 'critical',
      status: 'pending',
      evidence_image_path: null,
      detected_at: '2026-01-01T01:00:00Z',
      resolved_at: null,
      event_metadata: {},
      created_at: '2026-01-01T01:00:00Z',
      updated_at: '2026-01-01T01:00:00Z',
    },
  ];

  await page.route('**/api/alerts**', async (route) => {
    if (route.request().method() === 'GET' && new URL(route.request().url()).pathname === '/api/alerts') {
      await fulfillJson(route, alerts);
      return;
    }
    await route.fallback();
  });

  await page.route('**/api/cameras**', async (route) => {
    if (route.request().method() === 'GET' && new URL(route.request().url()).pathname === '/api/cameras') {
      await fulfillJson(route, [
        { id: 1, name: 'Cam 1', location: 'Floor 1', ip: '10.0.0.1', port: 80, status: 'active', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
      ]);
      return;
    }
    await route.fallback();
  });

  await page.goto('/alerts');
  await expect(page.locator('.el-table')).toContainText('pending');

  await page.locator('.el-table__body-wrapper .el-checkbox').nth(0).click();
  await expect(page.locator('.batch-bar')).toBeVisible();
  await expect(page.locator('.batch-bar')).toContainText('1 selected');

  await page.getByRole('button', { name: 'Clear' }).click();
  await expect(page.locator('.batch-bar')).not.toBeVisible();
});
