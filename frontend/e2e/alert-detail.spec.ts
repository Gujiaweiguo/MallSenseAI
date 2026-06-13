import { expect, test } from '@playwright/test';

import { fulfillJson, mockApi, mockLogin } from './helpers';

const mockCameras = [
  { id: 1, name: 'Hallway Cam', location: 'Floor 3', ip: '10.0.0.1', port: 80, status: 'active', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
];

const mockAlerts = [
  {
    id: 10,
    camera_id: 1,
    roi_id: 5,
    rule_id: 3,
    alert_type: 'obstruction_duration',
    severity: 'high',
    status: 'pending',
    evidence_image_path: '/evidence/10.jpg',
    detected_at: '2026-06-13T10:30:00Z',
    resolved_at: null,
    event_metadata: { zone_polygon: [[0.1, 0.2], [0.5, 0.2], [0.5, 0.6]], metric_value: 0.42 },
    created_at: '2026-06-13T10:30:00Z',
    updated_at: '2026-06-13T10:30:00Z',
  },
  {
    id: 11,
    camera_id: 1,
    roi_id: null,
    rule_id: null,
    alert_type: 'fire_smoke',
    severity: 'critical',
    status: 'confirmed',
    evidence_image_path: null,
    detected_at: '2026-06-13T11:00:00Z',
    resolved_at: null,
    event_metadata: {},
    created_at: '2026-06-13T11:00:00Z',
    updated_at: '2026-06-13T11:00:00Z',
  },
];

const mockWorkOrders = [
  { id: 1, alert_id: 11, assigned_to: 1, status: 'open', notes: 'Investigate immediately', created_at: '2026-06-13T11:01:00Z', updated_at: '2026-06-13T11:01:00Z' },
];

test('clicking alert row opens detail drawer with alert info', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/alerts', mockAlerts);
  await mockApi(page, 'GET', '/cameras', mockCameras);
  await mockApi(page, 'GET', '/work-orders', mockWorkOrders);
  await mockApi(page, 'GET', '/cameras/1', mockCameras[0]);

  await page.goto('/alerts');

  // Click first alert row
  await page.locator('.el-table__body-wrapper .el-table__row').first().click();

  // Drawer should open
  const drawer = page.locator('.el-drawer');
  await expect(drawer).toBeVisible();

  // Should show alert ID tag
  await expect(drawer).toContainText('Alert #10');

  // Should show severity and status
  await expect(drawer).toContainText('high');
  await expect(drawer).toContainText('pending');

  // Should show camera name (resolved from API)
  await expect(drawer).toContainText('Hallway Cam');

  // Should show metadata
  await expect(drawer).toContainText('metric_value');

  // Should show evidence section (evidence_image_path is set)
  await expect(drawer).toContainText('Evidence');
});

test('drawer shows related work orders for alert', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/alerts', [mockAlerts[1]]);
  await mockApi(page, 'GET', '/cameras', mockCameras);
  await mockApi(page, 'GET', '/work-orders', mockWorkOrders);
  await mockApi(page, 'GET', '/cameras/1', mockCameras[0]);

  await page.goto('/alerts');

  // Click the confirmed fire_smoke alert (has work order)
  await page.locator('.el-table__body-wrapper .el-table__row').first().click();

  const drawer = page.locator('.el-drawer');
  await expect(drawer).toBeVisible();

  // Should show related work orders section
  await expect(drawer).toContainText('Related Work Orders');
  await expect(drawer).toContainText('Investigate immediately');
  await expect(drawer).toContainText('open');
});

test('drawer closes when clicking close button', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/alerts', mockAlerts);
  await mockApi(page, 'GET', '/cameras', mockCameras);
  await mockApi(page, 'GET', '/work-orders', []);
  await mockApi(page, 'GET', '/cameras/1', mockCameras[0]);

  await page.goto('/alerts');
  await page.locator('.el-table__body-wrapper .el-table__row').first().click();

  const drawer = page.locator('.el-drawer');
  await expect(drawer).toBeVisible();

  // Close drawer
  await drawer.locator('.el-drawer__close-btn').click();
  await expect(drawer).not.toBeVisible();
});
