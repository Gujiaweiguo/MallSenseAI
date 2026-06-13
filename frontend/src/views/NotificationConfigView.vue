<template>
  <section class="page-card notif-config">
    <div class="notif-config__header">
      <div>
        <h2 class="page-title">{{ t('notification.title') }}</h2>
        <p class="page-subtitle">{{ t('notification.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="resetGroupForm">{{ t('common.button.createGroup') }}</el-button>
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
          <el-table-column prop="id" :label="t('common.table.id')" width="80" />
          <el-table-column prop="name" :label="t('common.table.name')" min-width="180" />
          <el-table-column :label="t('common.table.severities')" min-width="260">
            <template #default="{ row }">
              <div class="notif-config__tag-list">
                <el-tag
                  v-for="severity in row.channels.severities"
                  :key="severity"
                  :type="severityTagType(severity)"
                  size="small"
                >
                  {{ t('common.enum.alertSeverity.' + severity) }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="t('common.table.enabled')" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ t('common.enum.enabledDisabled.' + (row.enabled ? 'enabled' : 'disabled')) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('common.table.channelsCount')" width="150">
            <template #default="{ row }">{{ row.notification_channels.length }}</template>
          </el-table-column>
          <el-table-column :label="t('common.table.actions')" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click.stop="selectGroup(row)">{{ t('common.button.edit') }}</el-button>
              <el-button type="danger" link @click.stop="confirmDeleteGroup(row)">{{ t('common.button.delete') }}</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="empty-note">{{ t('common.empty.noGroups') }}</span>
          </template>
        </el-table>
      </el-col>

      <el-col :xs="24" :lg="8">
        <div class="notif-config__side-stack">
          <el-card shadow="never">
            <template #header>{{ selectedGroupId === null ? t('notification.createGroupTitle') : t('notification.editGroupTitle', { id: selectedGroupId }) }}</template>
            <el-form label-position="top" :model="groupForm" @submit.prevent="submitGroupForm">
              <el-form-item :label="t('notification.formName')" required>
                <el-input v-model="groupForm.name" :placeholder="t('notification.phGroupName')" />
              </el-form-item>
              <el-form-item :label="t('notification.formSeverities')">
                <el-checkbox-group v-model="groupForm.severities" class="notif-config__checkbox-list">
                  <el-checkbox label="low">{{ t('common.enum.alertSeverity.low') }}</el-checkbox>
                  <el-checkbox label="medium">{{ t('common.enum.alertSeverity.medium') }}</el-checkbox>
                  <el-checkbox label="high">{{ t('common.enum.alertSeverity.high') }}</el-checkbox>
                  <el-checkbox label="critical">{{ t('common.enum.alertSeverity.critical') }}</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item :label="t('notification.formEnabled')">
                <el-switch v-model="groupForm.enabled" />
              </el-form-item>
              <div class="notif-config__form-actions">
                <el-button @click="resetGroupForm">{{ t('common.button.reset') }}</el-button>
                <el-button type="primary" :loading="savingGroup" @click="submitGroupForm">
                  {{ selectedGroupId === null ? t('common.button.create') : t('common.button.save') }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card v-if="selectedGroup !== null" shadow="never">
            <template #header>
              <div class="notif-config__header">
                <span>{{ t('notification.channelsForGroup', { id: selectedGroup.id }) }}</span>
                <el-button size="small" type="primary" @click="openChannelForm">{{ t('common.button.addChannel') }}</el-button>
              </div>
            </template>

            <div class="notif-config__channel-list">
              <div
                v-for="channel in selectedGroup.notification_channels"
                :key="channel.id"
                class="notif-config__channel-row"
              >
                <div class="notif-config__channel-meta">
                  <el-tag size="small">{{ t('common.enum.channelType.' + channel.channel_type) }}</el-tag>
                  <el-tag :type="channel.enabled ? 'success' : 'info'" size="small">
                    {{ t('common.enum.enabledDisabled.' + (channel.enabled ? 'enabled' : 'disabled')) }}
                  </el-tag>
                </div>
                <div class="notif-config__channel-actions">
                  <el-button size="small" :loading="testingChannelId === channel.id" @click="handleTestChannel(channel.id)">
                    {{ t('common.button.test') }}
                  </el-button>
                  <el-button size="small" type="primary" @click="openEditChannelForm(channel)">{{ t('common.button.edit') }}</el-button>
                  <el-button size="small" type="danger" @click="confirmDeleteChannel(channel.id)">{{ t('common.button.delete') }}</el-button>
                </div>
              </div>
              <span v-if="selectedGroup.notification_channels.length === 0" class="empty-note">{{ t('common.empty.noChannels') }}</span>
            </div>

            <el-form
              v-if="channelFormVisible"
              label-position="top"
              :model="channelForm"
              class="notif-config__channel-form"
              @submit.prevent="submitChannelForm"
            >
              <el-form-item :label="t('notification.channelFormType')">
                <el-select
                  v-model="channelForm.channel_type"
                  class="notif-config__full"
                  :disabled="editingChannelId !== null"
                  @change="resetChannelConfig"
                >
                  <el-option :label="t('common.enum.channelType.wecom')" value="wecom" />
                  <el-option :label="t('common.enum.channelType.sms')" value="sms" />
                  <el-option :label="t('common.enum.channelType.email')" value="email" />
                </el-select>
              </el-form-item>

              <template v-if="channelForm.channel_type === 'wecom'">
                <el-form-item :label="t('notification.wecomWebhookUrl')" required>
                  <el-input v-model="channelForm.webhook_url" :placeholder="t('notification.phWebhookUrl')" />
                </el-form-item>
              </template>

              <template v-else-if="channelForm.channel_type === 'sms'">
                <el-form-item :label="t('notification.smsProvider')">
                  <el-select v-model="channelForm.provider" class="notif-config__full">
                    <el-option label="Stub" value="stub" />
                    <el-option label="Twilio" value="twilio" />
                  </el-select>
                </el-form-item>
                <el-form-item :label="t('notification.smsPhoneNumbers')" required>
                  <el-input v-model="channelForm.phone_numbers" :placeholder="`${t('notification.phPhone1')}, ${t('notification.phPhone2')}`" />
                </el-form-item>
                <template v-if="channelForm.provider === 'twilio'">
                  <el-form-item :label="t('notification.smsAccountSid')">
                    <el-input v-model="channelForm.account_sid" />
                  </el-form-item>
                  <el-form-item :label="t('notification.smsAuthToken')">
                    <el-input v-model="channelForm.auth_token" type="password" show-password />
                  </el-form-item>
                  <el-form-item :label="t('notification.smsFromNumber')">
                    <el-input v-model="channelForm.from_number" :placeholder="t('notification.phPhone3')" />
                  </el-form-item>
                </template>
              </template>

              <template v-else>
                <el-form-item :label="t('notification.emailToAddress')" required>
                  <el-input v-model="channelForm.to_address" :placeholder="t('notification.phEmail')" />
                </el-form-item>
                <el-form-item :label="t('notification.emailSmtpHost')">
                  <el-input v-model="channelForm.smtp_host" :placeholder="t('common.placeholderNotImplemented')" />
                </el-form-item>
                <el-form-item :label="t('notification.emailSmtpPort')">
                  <el-input-number v-model="channelForm.smtp_port" :min="1" :max="65535" class="notif-config__full" />
                </el-form-item>
              </template>

              <el-form-item :label="t('notification.channelFormEnabled')">
                <el-switch v-model="channelForm.enabled" />
              </el-form-item>
              <div class="notif-config__form-actions">
                <el-button @click="channelFormVisible = false">{{ t('common.button.cancel') }}</el-button>
                <el-button type="primary" :loading="savingChannel" @click="submitChannelForm">
                  {{ t('common.button.save') }}
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
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();
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
    ElMessage.error(t('notification.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

async function submitGroupForm(): Promise<void> {
  if (groupForm.name.trim().length === 0) {
    ElMessage.error(t('notification.toastNameRequired'));
    return;
  }
  if (groupForm.severities.length === 0) {
    ElMessage.error(t('notification.toastSeverityRequired'));
    return;
  }

  savingGroup.value = true;
  try {
    if (selectedGroupId.value === null) {
      const created = await createNotificationGroup(groupPayloadFromForm());
      ElMessage.success(t('notification.toastGroupCreated'));
      await loadGroups();
      selectGroup(created);
    } else {
      const updated = await updateNotificationGroup(selectedGroupId.value, groupPayloadFromForm());
      ElMessage.success(t('notification.toastGroupUpdated'));
      await loadGroups();
      selectGroup(updated);
    }
  } catch {
    ElMessage.error(t('notification.toastGroupSaveFailed'));
  } finally {
    savingGroup.value = false;
  }
}

async function confirmDeleteGroup(group: NotificationGroup): Promise<void> {
  try {
    await ElMessageBox.confirm(t('notification.deleteGroupConfirm', { id: group.id }), t('notification.deleteGroupTitle'), { type: 'warning' });
    await deleteNotificationGroup(group.id);
    ElMessage.success(t('notification.toastGroupDeleted'));
    if (selectedGroupId.value === group.id) {
      resetGroupForm();
    }
    await loadGroups();
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('notification.toastGroupDeleteFailed'));
  }
}

async function submitChannelForm(): Promise<void> {
  if (selectedGroupId.value === null) return;

  savingChannel.value = true;
  try {
    if (editingChannelId.value === null) {
      await createNotificationChannel(selectedGroupId.value, channelPayloadFromForm());
      ElMessage.success(t('notification.toastChannelCreated'));
    } else {
      await updateNotificationChannel(editingChannelId.value, {
        config: channelConfigFromForm(),
        enabled: channelForm.enabled,
      });
      ElMessage.success(t('notification.toastChannelUpdated'));
    }
    channelFormVisible.value = false;
    await loadGroups();
  } catch {
    ElMessage.error(t('notification.toastChannelSaveFailed'));
  } finally {
    savingChannel.value = false;
  }
}

async function confirmDeleteChannel(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm(t('notification.deleteChannelConfirm', { id }), t('notification.deleteChannelTitle'), { type: 'warning' });
    await deleteNotificationChannel(id);
    ElMessage.success(t('notification.toastChannelDeleted'));
    await loadGroups();
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('notification.toastChannelDeleteFailed'));
  }
}

async function handleTestChannel(id: number): Promise<void> {
  testingChannelId.value = id;
  try {
    const result = await testNotificationChannel(id);
    if (result.success) {
      ElMessage.success(t('notification.toastTestSucceeded', { id: result.channel_id }));
    } else {
      ElMessage.error(t('notification.toastTestFailed', { id: result.channel_id }));
    }
  } catch {
    ElMessage.error(t('notification.toastTestError'));
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
