import { expect, test } from '@playwright/test';

import { fulfillJson, mockApi, mockLogin } from './helpers';

test('scene list, detail, and create dialog work', async ({ page }) => {
  await mockLogin(page);

  let scenes = [
    {
      id: 1,
      camera_id: 1,
      name: 'North Entrance Scene',
      baseline_image_path: '/images/scene-1.jpg',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2,
      camera_id: 2,
      name: 'Corridor Scene',
      baseline_image_path: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ];

  await page.route('**/api/scenes*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && url.pathname === '/api/scenes') {
      await fulfillJson(route, scenes);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/scenes') {
      const body = request.postDataJSON() as { name: string; camera_id: number };
      const scene = {
        id: 3,
        camera_id: body.camera_id,
        name: body.name,
        baseline_image_path: null,
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      };
      scenes = [...scenes, scene];
      await fulfillJson(route, scene, 201);
      return;
    }

    await route.fallback();
  });

  await mockApi(page, 'GET', '/scenes/1', scenes[0]);
  await mockApi(page, 'GET', '/rois', []);

  await page.goto('/scenes');
  await expect(page.locator('.el-table')).toContainText('North Entrance Scene');
  await expect(page.locator('.el-table')).toContainText('Corridor Scene');

  await page.getByRole('link', { name: 'North Entrance Scene' }).click();
  await expect(page).toHaveURL('/scenes/1');
  await expect(page.locator('.scene-detail__info')).toContainText('North Entrance Scene');
  await expect(page.locator('.scene-detail__info')).toContainText('Camera ID');

  await page.goto('/scenes');
  await page.getByRole('button', { name: 'Create Scene' }).click();
  const dialog = page.getByRole('dialog');
  await page.locator('input[placeholder="Scene name"]').fill('Food Court Scene');
  await page.locator('.el-input-number input').fill('3');
  await dialog.getByRole('button', { name: 'Create', exact: true }).click();
  await expect(page.locator('.el-table')).toContainText('Food Court Scene');
});
