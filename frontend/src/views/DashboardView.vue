<template>
  <section class="dashboard-view">
    <div v-if="loading" class="dashboard-view__loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading dashboard&hellip;</span>
    </div>

    <template v-else>
      <!-- Summary Cards -->
      <el-row :gutter="16" class="dashboard-view__row">
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#409eff"><VideoCamera /></el-icon>
              <span class="stat-card__title">Cameras</span>
            </div>
            <div class="stat-card__values">
              <el-statistic title="Total" :value="stats.cameras_total" />
              <div class="stat-card__breakdown">
                <el-tag type="success" size="small">{{ stats.cameras_active }} active</el-tag>
                <el-tag v-if="stats.cameras_error > 0" type="danger" size="small">{{ stats.cameras_error }} error</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#67c23a"><PictureFilled /></el-icon>
              <span class="stat-card__title">Scenes</span>
            </div>
            <div class="stat-card__values">
              <el-statistic title="Total" :value="stats.scenes_total" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#e6a23c"><Bell /></el-icon>
              <span class="stat-card__title">Alerts</span>
            </div>
            <div class="stat-card__values">
              <el-statistic title="Total" :value="stats.alerts_total" />
              <div class="stat-card__breakdown">
                <el-tag type="warning" size="small">{{ stats.alerts_pending }} pending</el-tag>
                <el-tag type="success" size="small">{{ stats.alerts_resolved }} resolved</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#909399"><Tickets /></el-icon>
              <span class="stat-card__title">Work Orders</span>
            </div>
            <div class="stat-card__values">
              <el-statistic title="Total" :value="stats.work_orders_total" />
              <div class="stat-card__breakdown">
                <el-tag size="small">{{ stats.work_orders_open }} open</el-tag>
                <el-tag type="primary" size="small">{{ stats.work_orders_in_progress }} in progress</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Alert Severity Breakdown -->
      <el-card shadow="never" class="dashboard-view__section">
        <template #header>
          <span>Alert Severity Breakdown</span>
        </template>
        <div class="severity-chart">
          <div
            v-for="sev in severityEntries"
            :key="sev.key"
            class="severity-chart__row"
          >
            <span class="severity-chart__label">{{ sev.label }}</span>
            <div class="severity-chart__bar-wrapper">
              <div
                class="severity-chart__bar"
                :class="`severity-chart__bar--${sev.key}`"
                :style="{ width: sev.percent + '%' }"
              />
            </div>
            <span class="severity-chart__count">{{ sev.count }}</span>
          </div>
          <p v-if="severityTotal === 0" class="severity-chart__empty">No alerts recorded yet.</p>
        </div>
      </el-card>

      <!-- Recent Alerts Table -->
      <el-card shadow="never" class="dashboard-view__section">
        <template #header>
          <span>Recent Alerts</span>
        </template>
        <el-table :data="recentAlerts" stripe style="width: 100%" empty-text="No alerts found.">
          <el-table-column prop="alert_type" label="Type" min-width="120" />
          <el-table-column prop="severity" label="Severity" min-width="100">
            <template #default="{ row }">
              <el-tag :type="severityTagType(row.severity)" size="small" effect="dark">
                {{ row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="Status" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detected_at" label="Detected At" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.detected_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Loading,
  VideoCamera,
  PictureFilled,
  Bell,
  Tickets,
} from '@element-plus/icons-vue';

import { getDashboardStats, listAlerts } from '@/api/resources';
import type { Alert, AlertSeverity, AlertStatus, DashboardStats } from '@/api/types';

const FALLBACK_STATS: DashboardStats = {
  cameras_total: 0,
  cameras_active: 0,
  cameras_inactive: 0,
  cameras_error: 0,
  scenes_total: 0,
  alerts_total: 0,
  alerts_pending: 0,
  alerts_confirmed: 0,
  alerts_false_positive: 0,
  alerts_resolved: 0,
  alerts_by_severity: {},
  work_orders_total: 0,
  work_orders_open: 0,
  work_orders_in_progress: 0,
  work_orders_closed: 0,
};

const loading = ref(true);
const stats = ref<DashboardStats>({ ...FALLBACK_STATS });
const recentAlerts = ref<Alert[]>([]);

const severityEntries = computed(() => {
  const bySev = stats.value.alerts_by_severity;
  const keys = Object.keys(bySev).length > 0 ? Object.keys(bySev) : ['low', 'medium', 'high', 'critical'];
  const maxCount = Math.max(1, ...Object.values(bySev));
  return keys.map((key) => ({
    key,
    label: key.charAt(0).toUpperCase() + key.slice(1),
    count: bySev[key] ?? 0,
    percent: ((bySev[key] ?? 0) / maxCount) * 100,
  }));
});

const severityTotal = computed(() =>
  Object.values(stats.value.alerts_by_severity).reduce((sum, n) => sum + n, 0),
);

function severityTagType(severity: AlertSeverity): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    low: 'info',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  };
  return map[severity] ?? 'info';
}

function statusTagType(status: AlertStatus): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    new: 'danger',
    confirmed: 'warning',
    false_positive: 'info',
    resolved: 'success',
  };
  return map[status] ?? 'info';
}

function formatDateTime(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

onMounted(async () => {
  try {
    const [statsData, alertsData] = await Promise.all([
      getDashboardStats(),
      listAlerts({ limit: 5 }),
    ]);
    stats.value = statsData;
    recentAlerts.value = alertsData;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.dashboard-view {
  padding: 0;
}

.dashboard-view__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 200px;
  color: var(--ms-color-muted);
}

.dashboard-view__row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
}

.stat-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.stat-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stat-card__values {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-card__breakdown {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dashboard-view__section {
  margin-bottom: 20px;
}

/* Severity Chart (Pure CSS) */
.severity-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.severity-chart__row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.severity-chart__label {
  width: 64px;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  text-align: right;
  flex-shrink: 0;
}

.severity-chart__bar-wrapper {
  flex: 1;
  height: 22px;
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
  overflow: hidden;
}

.severity-chart__bar {
  height: 100%;
  border-radius: 4px;
  min-width: 0;
  transition: width 0.4s ease;
}

.severity-chart__bar--low {
  background-color: #67c23a;
}

.severity-chart__bar--medium {
  background-color: #e6a23c;
}

.severity-chart__bar--high {
  background-color: #f56c6c;
}

.severity-chart__bar--critical {
  background-color: #c45656;
}

.severity-chart__count {
  width: 36px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  text-align: right;
  flex-shrink: 0;
}

.severity-chart__empty {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin: 8px 0 0;
}
</style>
