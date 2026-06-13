import { expect, test } from '@playwright/test';

import { fulfillJson, mockLogin } from './helpers';

test('notification config page loads and displays groups', async ({ page }) => {
  await mockLogin(page);

  const groups = [
    {
      id: 1,
      name: 'Ops Team',
      channels: { severities: ['high', 'critical'] },
      enabled: true,
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-01T00:00:00Z',
      notification_channels: [
        {
          id: 1,
          group_id: 1,
          channel_type: 'wecom',
          config: { webhook_url: 'https://example.com/hook' },
          enabled: true,
        },
      ],
    },
    {
      id: 2,
      name: 'Management',
      channels: { severities: ['critical'] },
      enabled: false,
      created_at: '2026-06-02T00:00:00Z',
      updated_at: '2026-06-02T00:00:00Z',
      notification_channels: [],
    },
  ];

  await page.route('**/api/notification-groups**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET' && (url.pathname === '/api/notification-groups' || url.searchParams.has('limit'))) {
      await fulfillJson(route, groups);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/notification-groups') {
      const body = request.postDataJSON() as { name: string; severities: string[]; enabled: boolean };
      const created = {
        id: 3,
        name: body.name,
        channels: { severities: body.severities },
        enabled: body.enabled,
        created_at: '2026-06-13T00:00:00Z',
        updated_at: '2026-06-13T00:00:00Z',
        notification_channels: [],
      };
      groups.push(created);
      await fulfillJson(route, created, 201);
      return;
    }

    await route.fallback();
  });

  await page.goto('/notifications');

  await expect(page.locator('.el-table')).toContainText('Ops Team');
  await expect(page.locator('.el-table')).toContainText('Management');
  await expect(page.locator('.el-table')).toContainText('high');
  await expect(page.locator('.el-table')).toContainText('critical');
});

test('create notification group flow works', async ({ page }) => {
  await mockLogin(page);

  const groups: Array<Record<string, unknown>> = [];

  await page.route('**/api/notification-groups**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET') {
      await fulfillJson(route, groups);
      return;
    }

    if (request.method() === 'POST' && url.pathname === '/api/notification-groups') {
      const body = request.postDataJSON() as { name: string; severities: string[]; enabled: boolean };
      const created = {
        id: 1,
        name: body.name,
        channels: { severities: body.severities },
        enabled: body.enabled,
        created_at: '2026-06-13T00:00:00Z',
        updated_at: '2026-06-13T00:00:00Z',
        notification_channels: [],
      };
      groups.push(created);
      await fulfillJson(route, created, 201);
      return;
    }

    await route.fallback();
  });

  await page.goto('/notifications');

  // Fill form and create
  await page.locator('input[placeholder*="Notification group name"]').fill('Security Team');
  await page.getByLabel('High').check();
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  await expect(page.locator('.el-table')).toContainText('Security Team');
  await expect(page.locator('.el-table')).toContainText('high');
});

test('selecting a group shows its channels', async ({ page }) => {
  await mockLogin(page);

  const groups = [
    {
      id: 1,
      name: 'Ops Team',
      channels: { severities: ['high', 'critical'] },
      enabled: true,
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-01T00:00:00Z',
      notification_channels: [
        {
          id: 1,
          group_id: 1,
          channel_type: 'wecom',
          config: { webhook_url: 'https://example.com/hook' },
          enabled: true,
        },
        {
          id: 2,
          group_id: 1,
          channel_type: 'sms',
          config: { provider: 'stub', phone_numbers: ['+15550001111'] },
          enabled: false,
        },
      ],
    },
  ];

  await page.route('**/api/notification-groups**', async (route) => {
    if (route.request().method() === 'GET') {
      await fulfillJson(route, groups);
      return;
    }
    await route.fallback();
  });

  await page.goto('/notifications');

  // Click on the group row
  await page.locator('.el-table__row').first().click();

  // Channel card should be visible with channel info
  await expect(page.locator('.notif-config__channel-list')).toContainText('wecom');
  await expect(page.locator('.notif-config__channel-list')).toContainText('sms');
  await expect(page.locator('.notif-config__channel-list')).toContainText('Enabled');
  await expect(page.locator('.notif-config__channel-list')).toContainText('Disabled');
});

test('deleting a group removes it from the table', async ({ page }) => {
  await mockLogin(page);

  let groups = [
    {
      id: 1,
      name: 'Ops Team',
      channels: { severities: ['high'] },
      enabled: true,
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-01T00:00:00Z',
      notification_channels: [],
    },
  ];

  await page.route('**/api/notification-groups**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === 'GET') {
      await fulfillJson(route, groups);
      return;
    }

    if (request.method() === 'DELETE' && url.pathname === '/api/notification-groups/1') {
      groups = groups.filter((g) => g.id !== 1);
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    await route.fallback();
  });

  await page.goto('/notifications');

  await expect(page.locator('.el-table')).toContainText('Ops Team');

  // Click delete and confirm
  await page.locator('.el-table__row').first().getByRole('button', { name: 'Delete' }).click();
  await page.locator('.el-message-box').getByRole('button', { name: 'OK' }).click();

  // Group should be gone
  await expect(page.locator('.el-table')).not.toContainText('Ops Team');
});
