<template>
  <section class="page-card">
    <h2 class="page-title">Alerts</h2>
    <p class="page-subtitle">Alert center loaded from GET /api/alerts.</p>

    <div class="filter-bar">
      <el-select v-model="severityFilter" placeholder="Severity" clearable style="width: 160px" @change="currentPage = 1">
        <el-option label="All" value="" />
        <el-option label="Low" value="low" />
        <el-option label="Medium" value="medium" />
        <el-option label="High" value="high" />
        <el-option label="Critical" value="critical" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="Status" clearable style="width: 180px" @change="currentPage = 1">
        <el-option label="All" value="" />
        <el-option label="Pending" value="pending" />
        <el-option label="Confirmed" value="confirmed" />
        <el-option label="False Positive" value="false_positive" />
        <el-option label="Resolved" value="resolved" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="pagedAlerts" row-key="id" stripe @row-click="handleRowClick">
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="camera_id" label="Camera" width="110" />
      <el-table-column prop="alert_type" label="Type" min-width="180" />
      <el-table-column prop="severity" label="Severity" width="130">
        <template #default="{ row }">
          <el-tag :type="alertSeverityTagType(row.severity)">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="150">
        <template #default="{ row }">
          <el-tag :type="alertStatusTagType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Detected At" min-width="190">
        <template #default="{ row }">{{ formatDate(row.detected_at) }}</template>
      </el-table-column>
      <el-table-column label="Actions" width="260" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="success" size="small" :loading="acting === row.id" @click.stop="handleConfirm(row.id)">
              Confirm
            </el-button>
            <el-button type="warning" size="small" :loading="acting === row.id" @click.stop="handleFalsePositive(row.id)">
              False Positive
            </el-button>
          </template>
          <template v-else-if="row.status === 'confirmed'">
            <el-button type="primary" size="small" :loading="acting === row.id" @click.stop="handleResolve(row.id)">
              Resolve
            </el-button>
          </template>
          <template v-else>
            <el-tag type="info" disable-transitions>Done</el-tag>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No alerts found.</span>
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
import { computed, onMounted, ref, watch } from 'vue';

import AlertDetailDrawer from '@/components/AlertDetailDrawer.vue';
import {
  listAlerts,
  confirmAlert,
  markAlertFalsePositive,
  resolveAlert,
} from '@/api/resources';
import type { Alert } from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';
import { useAlertEvents } from '@/composables/useAlertEvents';
import { alertSeverityTagType, alertStatusTagType } from '@/utils/tagType';

const alerts = ref<Alert[]>([]);
const loading = ref(false);
const acting = ref<number | null>(null);
const currentPage = ref(1);
const pageSize = ref(10);
const severityFilter = ref('');
const statusFilter = ref('');
const alertWs = useAlertEvents();
const drawerVisible = ref(false);
const selectedAlert = ref<Alert | null>(null);

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
    alerts.value = await listAlerts({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error('Failed to load alerts.');
  } finally {
    loading.value = false;
  }
}

async function handleConfirm(id: number): Promise<void> {
  acting.value = id;
  try {
    await confirmAlert(id);
    ElMessage.success('Alert confirmed.');
    await loadAlerts();
  } catch {
    ElMessage.error('Failed to confirm alert.');
  } finally {
    acting.value = null;
  }
}

async function handleFalsePositive(id: number): Promise<void> {
  try {
    const { value: reason } = await ElMessageBox.prompt('Optional reason', 'Mark as False Positive', {
      confirmButtonText: 'Submit',
      cancelButtonText: 'Cancel',
      inputPlaceholder: 'Reason (optional)',
    });
    acting.value = id;
    await markAlertFalsePositive(id, reason || undefined);
    ElMessage.success('Alert marked as false positive.');
    await loadAlerts();
  } catch (err: unknown) {
    // User cancelled or API error
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error('Failed to mark alert as false positive.');
    }
  } finally {
    acting.value = null;
  }
}

async function handleResolve(id: number): Promise<void> {
  try {
    const { value: notes } = await ElMessageBox.prompt('Optional notes', 'Resolve Alert', {
      confirmButtonText: 'Resolve',
      cancelButtonText: 'Cancel',
      inputPlaceholder: 'Notes (optional)',
    });
    acting.value = id;
    await resolveAlert(id, notes || undefined);
    ElMessage.success('Alert resolved.');
    await loadAlerts();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error('Failed to resolve alert.');
    }
  } finally {
    acting.value = null;
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
