import { expect, test } from '@playwright/test';

import { mockApi, mockLogin } from './helpers';

test.beforeEach(async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/alerts', [
    {
      id: 1,
      camera_id: 1,
      roi_id: null,
      rule_id: null,
      alert_type: 'obstruction',
      severity: 'high',
      status: 'confirmed',
      evidence_image_path: null,
      detected_at: '2026-01-01T01:00:00Z',
      resolved_at: null,
      event_metadata: {},
      created_at: '2026-01-01T01:00:00Z',
      updated_at: '2026-01-01T01:00:00Z',
    },
  ]);
});

test('dashboard renders stats and severity breakdown', async ({ page }) => {
  await mockApi(page, 'GET', '/dashboard/stats', {
    cameras_total: 21,
    cameras_active: 18,
    cameras_inactive: 2,
    cameras_error: 1,
    scenes_total: 21,
    alerts_total: 10,
    alerts_pending: 3,
    alerts_confirmed: 2,
    alerts_false_positive: 1,
    alerts_resolved: 4,
    alerts_by_severity: { low: 2, medium: 3, high: 3, critical: 2 },
    work_orders_total: 5,
    work_orders_open: 2,
    work_orders_in_progress: 1,
    work_orders_closed: 2,
  });

  await page.goto('/');

  await expect(page.locator('.main-layout__title')).toHaveText('Dashboard');
  await expect(page.locator('.stat-card').nth(0)).toContainText('Cameras');
  await expect(page.locator('.stat-card').nth(0)).toContainText('21');
  await expect(page.locator('.stat-card').nth(1)).toContainText('Scenes');
  await expect(page.locator('.stat-card').nth(1)).toContainText('21');
  await expect(page.locator('.stat-card').nth(2)).toContainText('Alerts');
  await expect(page.locator('.stat-card').nth(2)).toContainText('10');
  await expect(page.locator('.stat-card').nth(3)).toContainText('Work Orders');
  await expect(page.locator('.stat-card').nth(3)).toContainText('5');
  await expect(page.locator('.severity-chart')).toContainText('Low');
  await expect(page.locator('.severity-chart')).toContainText('2');
  await expect(page.locator('.severity-chart')).toContainText('Medium');
  await expect(page.locator('.severity-chart')).toContainText('3');
  await expect(page.locator('.severity-chart')).toContainText('High');
  await expect(page.locator('.severity-chart')).toContainText('Critical');
  await expect(page.locator('.dashboard-view__section').first()).toContainText('Alert Severity Breakdown');
});
