<template>
  <el-drawer
    :model-value="visible"
    :title="t('alert.drawerTitle')"
    direction="rtl"
    size="50%"
    destroy-on-close
    @update:model-value="emit('update:visible', $event)"
  >
    <template v-if="alert !== null">
      <div class="alert-detail">
        <div class="alert-detail__header">
          <div class="alert-detail__title-row">
            <el-tag size="large" effect="dark">{{ t('alert.alertTag', { id: alert.id }) }}</el-tag>
            <el-tag :type="alertSeverityTagType(alert.severity)">{{ t('common.enum.alertSeverity.' + alert.severity) }}</el-tag>
            <el-tag :type="alertStatusTagType(alert.status)">{{ t('common.enum.alertStatus.' + alert.status) }}</el-tag>
          </div>
          <div class="alert-detail__timestamp">{{ t('alert.detectedAt', { date: formatDate(alert.detected_at) }) }}</div>
        </div>

        <section class="alert-detail__section">
          <h3 class="alert-detail__section-title">{{ t('alert.sectionOverview') }}</h3>
          <div class="alert-detail__info-grid">
            <div class="alert-detail__info-item">
              <span class="alert-detail__label">{{ t('alert.labelCamera') }}</span>
              <span>{{ cameraDisplay }}</span>
            </div>
            <div class="alert-detail__info-item">
              <span class="alert-detail__label">{{ t('alert.labelRoiId') }}</span>
              <span>{{ alert.roi_id ?? t('common.na') }}</span>
            </div>
            <div class="alert-detail__info-item">
              <span class="alert-detail__label">{{ t('alert.labelAlertType') }}</span>
              <span>{{ alert.alert_type }}</span>
            </div>
            <div class="alert-detail__info-item">
              <span class="alert-detail__label">{{ t('alert.labelRuleId') }}</span>
              <span>{{ alert.rule_id ?? t('common.na') }}</span>
            </div>
          </div>
        </section>

        <section v-if="alert.evidence_image_path" class="alert-detail__section">
          <h3 class="alert-detail__section-title">{{ t('alert.sectionEvidence') }}</h3>
          <el-image
            class="alert-detail__evidence-image"
            :src="`/api/alerts/${alert.id}/evidence`"
            fit="contain"
          >
            <template #error>
              <div class="alert-detail__evidence-fallback">
                {{ t('alert.evidencePath', { path: alert.evidence_image_path }) }}
              </div>
            </template>
          </el-image>
        </section>

        <section class="alert-detail__section">
          <h3 class="alert-detail__section-title">{{ t('alert.sectionMetadata') }}</h3>
          <div v-if="metadataEntries.length > 0" class="alert-detail__metadata-list">
            <div v-for="entry in metadataEntries" :key="entry.key" class="alert-detail__metadata-row">
              <span class="alert-detail__label">{{ entry.key }}</span>
              <pre class="alert-detail__metadata-value">{{ entry.value }}</pre>
            </div>
          </div>
          <span v-else class="empty-note">{{ t('common.empty.noDetectionMetadata') }}</span>
        </section>

        <section class="alert-detail__section">
          <h3 class="alert-detail__section-title">{{ t('alert.sectionWorkOrders') }}</h3>
          <el-table v-if="workOrders.length > 0" :data="workOrders" row-key="id" size="small" stripe>
            <el-table-column prop="id" :label="t('common.table.id')" width="80" />
            <el-table-column :label="t('common.table.status')" width="140">
              <template #default="{ row }">
                <el-tag :type="workOrderStatusTagType(row.status)">{{ t('common.enum.workOrderStatus.' + row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('common.table.assignedTo')" min-width="140">
              <template #default="{ row }">
                {{ row.assigned_to === null ? t('common.unassigned') : t('alert.userN', { id: row.assigned_to }) }}
              </template>
            </el-table-column>
            <el-table-column prop="notes" :label="t('common.table.notes')" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.notes ?? '—' }}
              </template>
            </el-table-column>
          </el-table>
          <span v-else-if="loadingWorkOrders" class="empty-note">{{ t('common.loading') }}</span>
          <span v-else class="empty-note">{{ t('common.empty.noWorkOrdersLinked') }}</span>
        </section>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { getCamera, listWorkOrders } from '@/api/resources';
import type { Alert, Camera, WorkOrder } from '@/api/types';
import { alertSeverityTagType, alertStatusTagType, workOrderStatusTagType } from '@/utils/tagType';

const { t } = useI18n();

const props = defineProps<{
  visible: boolean;
  alert: Alert | null;
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean];
}>();

const camera = ref<Camera | null>(null);
const cameraLoading = ref(false);
const workOrders = ref<WorkOrder[]>([]);
const loadingWorkOrders = ref(false);

const cameraDisplay = computed(() => {
  if (props.alert === null) return t('common.na');
  if (cameraLoading.value) return t('common.loading');
  if (camera.value === null) return `${t('alert.labelCamera')} #${props.alert.camera_id}`;
  return `${camera.value.name} (${camera.value.location})`;
});

const metadataEntries = computed(() => {
  if (props.alert === null) return [];
  return Object.entries(props.alert.event_metadata).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }));
});

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

async function loadCamera(cameraId: number): Promise<void> {
  cameraLoading.value = true;
  try {
    camera.value = await getCamera(cameraId);
  } catch {
    camera.value = null;
    ElMessage.error(t('alert.toastCameraFailed'));
  } finally {
    cameraLoading.value = false;
  }
}

async function loadWorkOrders(alertId: number): Promise<void> {
  loadingWorkOrders.value = true;
  try {
    const params = { alert_id: alertId };
    workOrders.value = await listWorkOrders(params);
  } catch {
    workOrders.value = [];
    ElMessage.error(t('alert.toastWorkOrdersFailed'));
  } finally {
    loadingWorkOrders.value = false;
  }
}

watch(
  () => [props.visible, props.alert?.id] as const,
  ([visible, alertId]) => {
    if (!visible || props.alert === null || alertId === undefined) {
      camera.value = null;
      workOrders.value = [];
      return;
    }
    void loadCamera(props.alert.camera_id);
    void loadWorkOrders(alertId);
  },
  { immediate: true },
);
</script>

<style scoped>
.alert-detail {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-5);
}

.alert-detail__header,
.alert-detail__section {
  padding: var(--ms-space-4);
  background: var(--ms-color-surface);
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-2);
}

.alert-detail__title-row {
  display: flex;
  align-items: center;
  gap: var(--ms-space-3);
  flex-wrap: wrap;
}

.alert-detail__timestamp {
  margin-top: var(--ms-space-3);
  color: var(--ms-color-muted);
  font-size: 14px;
}

.alert-detail__section-title {
  margin: 0 0 var(--ms-space-4);
  font-size: 16px;
  font-weight: 650;
  color: var(--ms-color-header-text);
}

.alert-detail__info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ms-space-4);
}

.alert-detail__info-item,
.alert-detail__metadata-row {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-2);
}

.alert-detail__label {
  color: var(--ms-color-muted);
  font-size: 13px;
  font-weight: 600;
}

.alert-detail__evidence-image {
  display: block;
  width: 100%;
  max-height: 400px;
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-1);
  background: #f8fafc;
}

.alert-detail__evidence-fallback,
.alert-detail__metadata-value {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.alert-detail__evidence-fallback {
  padding: var(--ms-space-4);
  color: var(--ms-color-muted);
}

.alert-detail__metadata-list {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
}

@media (max-width: 1200px) {
  .alert-detail__info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
