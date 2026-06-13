import { expect, test } from '@playwright/test';

import { fulfillJson, mockApi, mockLogin } from './helpers';

const mockEvents = [
  {
    id: 1,
    camera_id: 10,
    roi_id: 5,
    detector_type: 'yolo',
    confidence: 0.92,
    evidence_path: '/evidence/1.jpg',
    event_metadata: { label: 'bottle', area_ratio: 0.04, polygon: [[0.2, 0.2], [0.4, 0.2], [0.4, 0.4], [0.2, 0.4]] },
    detected_at: '2026-06-13T08:15:00Z',
  },
  {
    id: 2,
    camera_id: 20,
    roi_id: null,
    detector_type: 'yolo',
    confidence: 0.78,
    evidence_path: null,
    event_metadata: { label: 'fire' },
    detected_at: '2026-06-13T09:30:00Z',
  },
  {
    id: 3,
    camera_id: 10,
    roi_id: null,
    detector_type: 'image_compare',
    confidence: null,
    evidence_path: null,
    event_metadata: {},
    detected_at: '2026-06-13T10:00:00Z',
  },
];

test('detection events list loads and displays events', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/detection-events', mockEvents);

  await page.goto('/detection-events');

  await expect(page.locator('.el-table')).toContainText('92.0%');
  await expect(page.locator('.el-table')).toContainText('78.0%');
  await expect(page.locator('.el-table')).toContainText('N/A');
  await expect(page.locator('.el-table')).toContainText('yolo');
  await expect(page.locator('.el-table')).toContainText('image_compare');
});

test('clicking event row opens metadata dialog', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/detection-events', mockEvents);

  await page.goto('/detection-events');

  // Click first row
  await page.locator('.el-table__body-wrapper .el-table__row').first().click();

  // Dialog should open with metadata
  const dialog = page.locator('.el-dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('label');
  await expect(dialog).toContainText('bottle');
});

test('detector type filter works', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/detection-events', mockEvents);

  await page.goto('/detection-events');

  // All events visible
  await expect(page.locator('.el-table')).toContainText('yolo');
  await expect(page.locator('.el-table')).toContainText('image_compare');

  // Filter by YOLO
  await page.locator('.filter-bar .el-select').click();
  await page.locator('.el-select-dropdown:visible').getByText('YOLO', { exact: true }).click();

  // Only yolo events should be visible
  await expect(page.locator('.el-table')).toContainText('yolo');
  await expect(page.locator('.el-table')).not.toContainText('image_compare');
});

test('camera ID filter works', async ({ page }) => {
  await mockLogin(page);
  await mockApi(page, 'GET', '/detection-events', mockEvents);

  await page.goto('/detection-events');

  // Filter by camera 10
  await page.locator('.filter-bar input').first().fill('10');
  await page.keyboard.press('Enter');

  // Only camera 10 events visible
  const rows = page.locator('.el-table__body-wrapper .el-table__row');
  await expect(rows).toHaveCount(2);
});
