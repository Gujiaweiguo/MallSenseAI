<template>
  <section class="page-card">
    <h2 class="page-title">{{ t('alert.title') }}</h2>
    <p class="page-subtitle">{{ t('alert.subtitle') }}</p>

    <div class="filter-bar">
      <el-select v-model="severityFilter" :placeholder="t('alert.filterSeverity')" clearable style="width: 160px" @change="currentPage = 1">
        <el-option :label="t('common.all')" value="" />
        <el-option :label="t('common.enum.alertSeverity.low')" value="low" />
        <el-option :label="t('common.enum.alertSeverity.medium')" value="medium" />
        <el-option :label="t('common.enum.alertSeverity.high')" value="high" />
        <el-option :label="t('common.enum.alertSeverity.critical')" value="critical" />
      </el-select>
      <el-select v-model="statusFilter" :placeholder="t('alert.filterStatus')" clearable style="width: 180px" @change="currentPage = 1">
        <el-option :label="t('common.all')" value="" />
        <el-option :label="t('common.enum.alertStatus.pending')" value="pending" />
        <el-option :label="t('common.enum.alertStatus.confirmed')" value="confirmed" />
        <el-option :label="t('common.enum.alertStatus.false_positive')" value="false_positive" />
        <el-option :label="t('common.enum.alertStatus.resolved')" value="resolved" />
      </el-select>
      <el-button :loading="exporting" style="margin-left: auto" @click="handleExport">{{ t('common.button.export') }}</el-button>
    </div>

    <div v-if="selectedAlerts.length > 0" class="batch-bar">
      <span>{{ t('alert.nSelected', { n: selectedAlerts.length }) }}</span>
      <el-button type="success" size="small" :loading="batching" @click="handleBatchConfirm">
        {{ t('common.button.batchConfirm') }}
      </el-button>
      <el-button type="primary" size="small" :loading="batching" @click="handleBatchResolve">
        {{ t('common.button.batchResolve') }}
      </el-button>
      <el-button size="small" @click="clearSelection">{{ t('common.button.clear') }}</el-button>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="pagedAlerts"
      row-key="id"
      stripe
      @row-click="handleRowClick"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" :label="t('common.table.id')" width="90" />
      <el-table-column :label="t('common.table.camera')" width="140">
        <template #default="{ row }">
          {{ cameraDisplay(row.camera_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="alert_type" :label="t('common.table.type')" min-width="180" />
      <el-table-column prop="severity" :label="t('common.table.severity')" width="130">
        <template #default="{ row }">
          <el-tag :type="alertSeverityTagType(row.severity)">{{ t('common.enum.alertSeverity.' + row.severity) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" :label="t('common.table.status')" width="150">
        <template #default="{ row }">
          <el-tag :type="alertStatusTagType(row.status)">{{ t('common.enum.alertStatus.' + row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.table.detectedAt')" min-width="190">
        <template #default="{ row }">{{ formatDate(row.detected_at) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.table.actions')" width="260" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="success" size="small" :loading="acting === row.id" @click.stop="handleConfirm(row.id)">
              {{ t('common.button.confirm') }}
            </el-button>
            <el-button type="warning" size="small" :loading="acting === row.id" @click.stop="handleFalsePositive(row.id)">
              {{ t('alert.falsePositive') }}
            </el-button>
          </template>
          <template v-else-if="row.status === 'confirmed'">
            <el-button type="primary" size="small" :loading="acting === row.id" @click.stop="handleResolve(row.id)">
              {{ t('common.button.resolve') }}
            </el-button>
          </template>
          <template v-else>
            <el-tag type="info" disable-transitions>{{ t('common.done') }}</el-tag>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noAlerts') }}</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredAlerts.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>

    <AlertDetailDrawer v-model:visible="drawerVisible" :alert="selectedAlert" />
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import type { TableInstance } from 'element-plus';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import AlertDetailDrawer from '@/components/AlertDetailDrawer.vue';
import {
  listAlerts,
  listCameras,
  confirmAlert,
  markAlertFalsePositive,
  resolveAlert,
  exportAlerts,
  batchAlerts,
} from '@/api/resources';
import type { Alert, Camera } from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';
import { useAlertEvents } from '@/composables/useAlertEvents';
import { alertSeverityTagType, alertStatusTagType } from '@/utils/tagType';

const { t } = useI18n();

const alerts = ref<Alert[]>([]);
const cameras = ref<Camera[]>([]);
const loading = ref(false);
const exporting = ref(false);
const acting = ref<number | null>(null);
const batching = ref(false);
const tableRef = ref<TableInstance>();
const selectedAlerts = ref<Alert[]>([]);
const currentPage = ref(1);
const pageSize = ref(10);
const severityFilter = ref('');
const statusFilter = ref('');
const alertWs = useAlertEvents();
const drawerVisible = ref(false);
const selectedAlert = ref<Alert | null>(null);

const cameraMap = computed(() => {
  const map = new Map<number, Camera>();
  for (const c of cameras.value) {
    map.set(c.id, c);
  }
  return map;
});

function cameraDisplay(cameraId: number): string {
  const cam = cameraMap.value.get(cameraId);
  if (!cam) return `#${cameraId}`;
  return cam.name;
}

const filteredAlerts = computed(() => {
  let result = alerts.value;
  if (severityFilter.value) {
    result = result.filter((a) => a.severity === severityFilter.value);
  }
  if (statusFilter.value) {
    result = result.filter((a) => a.status === statusFilter.value);
  }
  return result;
});

const pagedAlerts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredAlerts.value.slice(start, start + pageSize.value);
});

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function handleRowClick(row: Alert): void {
  selectedAlert.value = row;
  drawerVisible.value = true;
}

async function loadAlerts(): Promise<void> {
  loading.value = true;
  try {
    const [alertList, cameraList] = await Promise.all([
      listAlerts({ limit: DEFAULT_LIST_LIMIT }),
      listCameras({ limit: DEFAULT_LIST_LIMIT }),
    ]);
    alerts.value = alertList;
    cameras.value = cameraList;
  } catch {
    ElMessage.error(t('alert.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

async function handleExport(): Promise<void> {
  exporting.value = true;
  try {
    const blob = await exportAlerts({
      severity: severityFilter.value || undefined,
      status: statusFilter.value || undefined,
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'alerts.csv';
    link.click();
    URL.revokeObjectURL(url);
    ElMessage.success(t('alert.toastExported'));
  } catch {
    ElMessage.error(t('alert.toastExportFailed'));
  } finally {
    exporting.value = false;
  }
}

async function handleConfirm(id: number): Promise<void> {
  acting.value = id;
  try {
    await confirmAlert(id);
    ElMessage.success(t('alert.toastConfirmed'));
    await loadAlerts();
  } catch {
    ElMessage.error(t('alert.toastConfirmFailed'));
  } finally {
    acting.value = null;
  }
}

async function handleFalsePositive(id: number): Promise<void> {
  try {
    const { value: reason } = await ElMessageBox.prompt(t('alert.fpReasonLabel'), t('alert.fpTitle'), {
      confirmButtonText: t('common.submit'),
      cancelButtonText: t('common.button.cancel'),
      inputPlaceholder: t('alert.fpReasonPlaceholder'),
    });
    acting.value = id;
    await markAlertFalsePositive(id, reason || undefined);
    ElMessage.success(t('alert.toastFalsePositive'));
    await loadAlerts();
  } catch (err: unknown) {
    // User cancelled or API error
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error(t('alert.toastFalsePositiveFailed'));
    }
  } finally {
    acting.value = null;
  }
}

async function handleResolve(id: number): Promise<void> {
  try {
    const { value: notes } = await ElMessageBox.prompt(t('alert.resolveNotesLabel'), t('alert.resolveTitle'), {
      confirmButtonText: t('common.button.resolve'),
      cancelButtonText: t('common.button.cancel'),
      inputPlaceholder: t('alert.resolveNotesPlaceholder'),
    });
    acting.value = id;
    await resolveAlert(id, notes || undefined);
    ElMessage.success(t('alert.toastResolved'));
    await loadAlerts();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error(t('alert.toastResolveFailed'));
    }
  } finally {
    acting.value = null;
  }
}

function handleSelectionChange(rows: Alert[]): void {
  selectedAlerts.value = rows;
}

function clearSelection(): void {
  tableRef.value?.clearSelection();
}

async function handleBatchConfirm(): Promise<void> {
  const ids = selectedAlerts.value.map((a) => a.id);
  try {
    await ElMessageBox.confirm(t('alert.batchConfirmMsg', { n: ids.length }), t('alert.batchConfirmTitle'), {
      confirmButtonText: t('common.button.confirm'),
      cancelButtonText: t('common.button.cancel'),
      type: 'warning',
    });
    batching.value = true;
    const result = await batchAlerts(ids, 'confirm');
    ElMessage.success(t('alert.batchConfirmed', { n: result.processed }));
    if (result.failed.length > 0) {
      ElMessage.warning(t('alert.batchSkipped', { n: result.failed.length }));
    }
    clearSelection();
    await loadAlerts();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error(t('alert.batchConfirmFailed'));
    }
  } finally {
    batching.value = false;
  }
}

async function handleBatchResolve(): Promise<void> {
  const ids = selectedAlerts.value.map((a) => a.id);
  try {
    await ElMessageBox.confirm(t('alert.batchResolveMsg', { n: ids.length }), t('alert.batchResolveTitle'), {
      confirmButtonText: t('common.button.resolve'),
      cancelButtonText: t('common.button.cancel'),
      type: 'warning',
    });
    batching.value = true;
    const result = await batchAlerts(ids, 'resolve');
    ElMessage.success(t('alert.batchResolved', { n: result.processed }));
    if (result.failed.length > 0) {
      ElMessage.warning(t('alert.batchSkipped', { n: result.failed.length }));
    }
    clearSelection();
    await loadAlerts();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error(t('alert.batchResolveFailed'));
    }
  } finally {
    batching.value = false;
  }
}

watch(() => alertWs.lastEvent.value, (event) => {
  if (!event) return;
  if (event.event_type === 'created') {
    void loadAlerts();
  } else if (
    event.event_type === 'confirmed' ||
    event.event_type === 'resolved' ||
    event.event_type === 'false_positive' ||
    event.event_type === 'escalated'
  ) {
    const idx = alerts.value.findIndex((a) => a.id === event.alert_id);
    if (idx !== -1) {
      void loadAlerts();
    }
  }
});

onMounted(() => {
  void loadAlerts();
});
</script>

<style scoped>
.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: var(--el-color-primary-light-9, #ecf5ff);
  border-radius: 6px;
  font-size: 14px;
}
</style>
