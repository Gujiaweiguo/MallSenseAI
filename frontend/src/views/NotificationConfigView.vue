<template>
  <section class="page-card notif-config">
    <div class="notif-config__header">
      <div>
        <h2 class="page-title">Notification Configuration</h2>
        <p class="page-subtitle">Manage alert notification groups and delivery channels.</p>
      </div>
      <el-button type="primary" @click="resetGroupForm">Create Group</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-table
          v-loading="loading"
          :data="groups"
          row-key="id"
          stripe
          highlight-current-row
          :current-row-key="selectedGroupId"
          @row-click="selectGroup"
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="name" label="Name" min-width="180" />
          <el-table-column label="Severities" min-width="260">
            <template #default="{ row }">
              <div class="notif-config__tag-list">
                <el-tag
                  v-for="severity in row.channels.severities"
                  :key="severity"
                  :type="severityTagType(severity)"
                  size="small"
                >
                  {{ severity }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Enabled" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Enabled' : 'Disabled' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Channels Count" width="150">
            <template #default="{ row }">{{ row.notification_channels.length }}</template>
          </el-table-column>
          <el-table-column label="Actions" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click.stop="selectGroup(row)">Edit</el-button>
              <el-button type="danger" link @click.stop="confirmDeleteGroup(row)">Delete</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="empty-note">No notification groups configured.</span>
          </template>
        </el-table>
      </el-col>

      <el-col :xs="24" :lg="8">
        <div class="notif-config__side-stack">
          <el-card shadow="never">
            <template #header>{{ selectedGroupId === null ? 'Create Group' : `Edit Group #${selectedGroupId}` }}</template>
            <el-form label-position="top" :model="groupForm" @submit.prevent="submitGroupForm">
              <el-form-item label="Name" required>
                <el-input v-model="groupForm.name" placeholder="Notification group name" />
              </el-form-item>
              <el-form-item label="Severities">
                <el-checkbox-group v-model="groupForm.severities" class="notif-config__checkbox-list">
                  <el-checkbox label="low">Low</el-checkbox>
                  <el-checkbox label="medium">Medium</el-checkbox>
                  <el-checkbox label="high">High</el-checkbox>
                  <el-checkbox label="critical">Critical</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item label="Enabled">
                <el-switch v-model="groupForm.enabled" />
              </el-form-item>
              <div class="notif-config__form-actions">
                <el-button @click="resetGroupForm">Reset</el-button>
                <el-button type="primary" :loading="savingGroup" @click="submitGroupForm">
                  {{ selectedGroupId === null ? 'Create' : 'Save' }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card v-if="selectedGroup !== null" shadow="never">
            <template #header>
              <div class="notif-config__header">
                <span>Channels for Group #{{ selectedGroup.id }}</span>
                <el-button size="small" type="primary" @click="openChannelForm">Add Channel</el-button>
              </div>
            </template>

            <div class="notif-config__channel-list">
              <div
                v-for="channel in selectedGroup.notification_channels"
                :key="channel.id"
                class="notif-config__channel-row"
              >
                <div class="notif-config__channel-meta">
                  <el-tag size="small">{{ channel.channel_type }}</el-tag>
                  <el-tag :type="channel.enabled ? 'success' : 'info'" size="small">
                    {{ channel.enabled ? 'Enabled' : 'Disabled' }}
                  </el-tag>
                </div>
                <div class="notif-config__channel-actions">
                  <el-button size="small" :loading="testingChannelId === channel.id" @click="handleTestChannel(channel.id)">
                    Test
                  </el-button>
                  <el-button size="small" type="primary" @click="openEditChannelForm(channel)">Edit</el-button>
                  <el-button size="small" type="danger" @click="confirmDeleteChannel(channel.id)">Delete</el-button>
                </div>
              </div>
              <span v-if="selectedGroup.notification_channels.length === 0" class="empty-note">No channels configured.</span>
            </div>

            <el-form
              v-if="channelFormVisible"
              label-position="top"
              :model="channelForm"
              class="notif-config__channel-form"
              @submit.prevent="submitChannelForm"
            >
              <el-form-item label="Channel Type">
                <el-select
                  v-model="channelForm.channel_type"
                  class="notif-config__full"
                  :disabled="editingChannelId !== null"
                  @change="resetChannelConfig"
                >
                  <el-option label="WeCom" value="wecom" />
                  <el-option label="SMS" value="sms" />
                  <el-option label="Email" value="email" />
                </el-select>
              </el-form-item>

              <template v-if="channelForm.channel_type === 'wecom'">
                <el-form-item label="Webhook URL" required>
                  <el-input v-model="channelForm.webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?..." />
                </el-form-item>
              </template>

              <template v-else-if="channelForm.channel_type === 'sms'">
                <el-form-item label="Provider">
                  <el-select v-model="channelForm.provider" class="notif-config__full">
                    <el-option label="Stub" value="stub" />
                    <el-option label="Twilio" value="twilio" />
                  </el-select>
                </el-form-item>
                <el-form-item label="Phone Numbers" required>
                  <el-input v-model="channelForm.phone_numbers" placeholder="+15550001111, +15550002222" />
                </el-form-item>
                <template v-if="channelForm.provider === 'twilio'">
                  <el-form-item label="Account SID">
                    <el-input v-model="channelForm.account_sid" />
                  </el-form-item>
                  <el-form-item label="Auth Token">
                    <el-input v-model="channelForm.auth_token" type="password" show-password />
                  </el-form-item>
                  <el-form-item label="From Number">
                    <el-input v-model="channelForm.from_number" placeholder="+15550000000" />
                  </el-form-item>
                </template>
              </template>

              <template v-else>
                <el-form-item label="To Address" required>
                  <el-input v-model="channelForm.to_address" placeholder="ops@example.com" />
                </el-form-item>
                <el-form-item label="SMTP Host">
                  <el-input v-model="channelForm.smtp_host" placeholder="Placeholder — not implemented yet" />
                </el-form-item>
                <el-form-item label="SMTP Port">
                  <el-input-number v-model="channelForm.smtp_port" :min="1" :max="65535" class="notif-config__full" />
                </el-form-item>
              </template>

              <el-form-item label="Enabled">
                <el-switch v-model="channelForm.enabled" />
              </el-form-item>
              <div class="notif-config__form-actions">
                <el-button @click="channelFormVisible = false">Cancel</el-button>
                <el-button type="primary" :loading="savingChannel" @click="submitChannelForm">
                  {{ editingChannelId === null ? 'Save' : 'Update' }}
                </el-button>
              </div>
            </el-form>
          </el-card>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';

import {
  createNotificationChannel,
  createNotificationGroup,
  deleteNotificationChannel,
  deleteNotificationGroup,
  listNotificationGroups,
  testNotificationChannel,
  updateNotificationChannel,
  updateNotificationGroup,
} from '@/api/resources';
import type {
  AlertSeverity,
  NotificationChannel,
  NotificationChannelCreatePayload,
  NotificationChannelType,
  NotificationGroup,
  NotificationGroupCreatePayload,
} from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

type TagType = '' | 'success' | 'warning' | 'danger' | 'info';
type SmsProvider = 'stub' | 'twilio';

interface GroupForm {
  name: string;
  severities: AlertSeverity[];
  enabled: boolean;
}

interface ChannelForm {
  channel_type: NotificationChannelType;
  webhook_url: string;
  provider: SmsProvider;
  phone_numbers: string;
  account_sid: string;
  auth_token: string;
  from_number: string;
  to_address: string;
  smtp_host: string;
  smtp_port: number;
  enabled: boolean;
}

const groups = ref<NotificationGroup[]>([]);
const loading = ref(false);
const savingGroup = ref(false);
const savingChannel = ref(false);
const selectedGroupId = ref<number | null>(null);
const editingChannelId = ref<number | null>(null);
const channelFormVisible = ref(false);
const testingChannelId = ref<number | null>(null);
const groupForm = reactive<GroupForm>(defaultGroupForm());
const channelForm = reactive<ChannelForm>(defaultChannelForm());

const selectedGroup = computed(() => {
  if (selectedGroupId.value === null) return null;
  return groups.value.find((group) => group.id === selectedGroupId.value) ?? null;
});

function defaultGroupForm(): GroupForm {
  return {
    name: '',
    severities: ['medium', 'high', 'critical'],
    enabled: true,
  };
}

function defaultChannelForm(): ChannelForm {
  return {
    channel_type: 'wecom',
    webhook_url: '',
    provider: 'stub',
    phone_numbers: '',
    account_sid: '',
    auth_token: '',
    from_number: '',
    to_address: '',
    smtp_host: '',
    smtp_port: 25,
    enabled: true,
  };
}

function assignGroupForm(next: GroupForm): void {
  groupForm.name = next.name;
  groupForm.severities = [...next.severities];
  groupForm.enabled = next.enabled;
}

function assignChannelForm(next: ChannelForm): void {
  channelForm.channel_type = next.channel_type;
  channelForm.webhook_url = next.webhook_url;
  channelForm.provider = next.provider;
  channelForm.phone_numbers = next.phone_numbers;
  channelForm.account_sid = next.account_sid;
  channelForm.auth_token = next.auth_token;
  channelForm.from_number = next.from_number;
  channelForm.to_address = next.to_address;
  channelForm.smtp_host = next.smtp_host;
  channelForm.smtp_port = next.smtp_port;
  channelForm.enabled = next.enabled;
}

function resetGroupForm(): void {
  selectedGroupId.value = null;
  channelFormVisible.value = false;
  assignGroupForm(defaultGroupForm());
}

function resetChannelConfig(): void {
  const channelType = channelForm.channel_type;
  assignChannelForm({ ...defaultChannelForm(), channel_type: channelType });
}

function openChannelForm(): void {
  editingChannelId.value = null;
  assignChannelForm(defaultChannelForm());
  channelFormVisible.value = true;
}

function openEditChannelForm(channel: NotificationChannel): void {
  editingChannelId.value = channel.id;
  const config = channel.config;
  const form = defaultChannelForm();
  form.channel_type = channel.channel_type;
  if (channel.channel_type === 'wecom') {
    form.webhook_url = (config.webhook_url as string) ?? '';
  } else if (channel.channel_type === 'sms') {
    form.provider = ((config.provider as SmsProvider) ?? 'stub');
    form.phone_numbers = Array.isArray(config.phone_numbers)
      ? (config.phone_numbers as string[]).join(', ')
      : '';
    form.account_sid = (config.account_sid as string) ?? '';
    form.auth_token = (config.auth_token as string) ?? '';
    form.from_number = (config.from_number as string) ?? '';
  } else {
    form.to_address = (config.to_address as string) ?? '';
    form.smtp_host = (config.smtp_host as string) ?? '';
    form.smtp_port = (config.smtp_port as number) ?? 25;
  }
  form.enabled = channel.enabled;
  assignChannelForm(form);
  channelFormVisible.value = true;
}

function selectGroup(group: NotificationGroup): void {
  selectedGroupId.value = group.id;
  channelFormVisible.value = false;
  editingChannelId.value = null;
  assignGroupForm({
    name: group.name,
    severities: toAlertSeverities(group.channels.severities),
    enabled: group.enabled,
  });
}

function toAlertSeverities(values: string[]): AlertSeverity[] {
  const valid = new Set<AlertSeverity>(['low', 'medium', 'high', 'critical']);
  return values.filter((value): value is AlertSeverity => valid.has(value as AlertSeverity));
}

function severityTagType(severity: string): TagType {
  const map: Record<string, TagType> = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  };
  return map[severity] ?? 'info';
}

function groupPayloadFromForm(): NotificationGroupCreatePayload {
  return {
    name: groupForm.name,
    severities: [...groupForm.severities],
    enabled: groupForm.enabled,
  };
}

function phoneNumbersFromInput(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function channelConfigFromForm(): Record<string, unknown> {
  if (channelForm.channel_type === 'wecom') {
    return { webhook_url: channelForm.webhook_url };
  }

  if (channelForm.channel_type === 'sms') {
    const baseConfig: Record<string, unknown> = {
      provider: channelForm.provider,
      phone_numbers: phoneNumbersFromInput(channelForm.phone_numbers),
    };
    if (channelForm.provider === 'twilio') {
      baseConfig.account_sid = channelForm.account_sid;
      baseConfig.auth_token = channelForm.auth_token;
      baseConfig.from_number = channelForm.from_number;
    }
    return baseConfig;
  }

  return {
    to_address: channelForm.to_address,
    smtp_host: channelForm.smtp_host,
    smtp_port: channelForm.smtp_port,
  };
}

function channelPayloadFromForm(): NotificationChannelCreatePayload {
  return {
    channel_type: channelForm.channel_type,
    config: channelConfigFromForm(),
    enabled: channelForm.enabled,
  };
}

async function loadGroups(): Promise<void> {
  loading.value = true;
  try {
    groups.value = await listNotificationGroups({ limit: DEFAULT_LIST_LIMIT });
    if (selectedGroupId.value !== null) {
      const selected = selectedGroup.value;
      if (selected === null) {
        resetGroupForm();
      } else {
        selectGroup(selected);
      }
    }
  } catch {
    ElMessage.error('Failed to load notification groups.');
  } finally {
    loading.value = false;
  }
}

async function submitGroupForm(): Promise<void> {
  if (groupForm.name.trim().length === 0) {
    ElMessage.error('Group name is required.');
    return;
  }
  if (groupForm.severities.length === 0) {
    ElMessage.error('Select at least one severity.');
    return;
  }

  savingGroup.value = true;
  try {
    if (selectedGroupId.value === null) {
      const created = await createNotificationGroup(groupPayloadFromForm());
      ElMessage.success('Notification group created.');
      await loadGroups();
      selectGroup(created);
    } else {
      const updated = await updateNotificationGroup(selectedGroupId.value, groupPayloadFromForm());
      ElMessage.success('Notification group updated.');
      await loadGroups();
      selectGroup(updated);
    }
  } catch {
    ElMessage.error('Failed to save notification group.');
  } finally {
    savingGroup.value = false;
  }
}

async function confirmDeleteGroup(group: NotificationGroup): Promise<void> {
  try {
    await ElMessageBox.confirm(`Delete notification group #${group.id}?`, 'Delete Notification Group', { type: 'warning' });
    await deleteNotificationGroup(group.id);
    ElMessage.success('Notification group deleted.');
    if (selectedGroupId.value === group.id) {
      resetGroupForm();
    }
    await loadGroups();
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error('Failed to delete notification group.');
  }
}

async function submitChannelForm(): Promise<void> {
  if (selectedGroupId.value === null) return;

  savingChannel.value = true;
  try {
    if (editingChannelId.value === null) {
      await createNotificationChannel(selectedGroupId.value, channelPayloadFromForm());
      ElMessage.success('Notification channel created.');
    } else {
      await updateNotificationChannel(editingChannelId.value, {
        config: channelConfigFromForm(),
        enabled: channelForm.enabled,
      });
      ElMessage.success('Notification channel updated.');
    }
    channelFormVisible.value = false;
    await loadGroups();
  } catch {
    ElMessage.error('Failed to save notification channel.');
  } finally {
    savingChannel.value = false;
  }
}

async function confirmDeleteChannel(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm(`Delete notification channel #${id}?`, 'Delete Notification Channel', { type: 'warning' });
    await deleteNotificationChannel(id);
    ElMessage.success('Notification channel deleted.');
    await loadGroups();
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error('Failed to delete notification channel.');
  }
}

async function handleTestChannel(id: number): Promise<void> {
  testingChannelId.value = id;
  try {
    const result = await testNotificationChannel(id);
    if (result.success) {
      ElMessage.success(`Notification channel #${result.channel_id} test succeeded.`);
    } else {
      ElMessage.error(`Notification channel #${result.channel_id} test failed.`);
    }
  } catch {
    ElMessage.error('Failed to test notification channel.');
  } finally {
    testingChannelId.value = null;
  }
}

onMounted(() => {
  void loadGroups();
});
</script>

<style scoped>
.notif-config__header,
.notif-config__form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.notif-config__full {
  width: 100%;
}

.notif-config__form-actions {
  justify-content: flex-end;
}

.notif-config__side-stack,
.notif-config__channel-list,
.notif-config__channel-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.notif-config__tag-list,
.notif-config__channel-meta,
.notif-config__channel-actions,
.notif-config__checkbox-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.notif-config__channel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-1);
}

.notif-config__channel-form {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--ms-color-border);
}
</style>
