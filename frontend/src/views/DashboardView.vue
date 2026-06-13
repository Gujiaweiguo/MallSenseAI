<template>
  <section class="dashboard-view">
    <div v-if="loading" class="dashboard-view__loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>{{ t('dashboard.loading') }}</span>
    </div>

    <template v-else>
      <!-- Summary Cards -->
      <el-row :gutter="16" class="dashboard-view__row">
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#409eff"><VideoCamera /></el-icon>
              <span class="stat-card__title">{{ t('dashboard.cameras') }}</span>
            </div>
            <div class="stat-card__values">
              <el-statistic :title="t('dashboard.total')" :value="stats.cameras_total" />
              <div class="stat-card__breakdown">
                <el-tag type="success" size="small">{{ t('dashboard.nActive', { n: stats.cameras_active }) }}</el-tag>
                <el-tag v-if="stats.cameras_error > 0" type="danger" size="small">{{ t('dashboard.nError', { n: stats.cameras_error }) }}</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#67c23a"><PictureFilled /></el-icon>
              <span class="stat-card__title">{{ t('dashboard.scenes') }}</span>
            </div>
            <div class="stat-card__values">
              <el-statistic :title="t('dashboard.total')" :value="stats.scenes_total" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#e6a23c"><Bell /></el-icon>
              <span class="stat-card__title">{{ t('dashboard.alerts') }}</span>
            </div>
            <div class="stat-card__values">
              <el-statistic :title="t('dashboard.total')" :value="stats.alerts_total" />
              <div class="stat-card__breakdown">
                <el-tag type="warning" size="small">{{ t('dashboard.nPending', { n: stats.alerts_pending }) }}</el-tag>
                <el-tag type="success" size="small">{{ t('dashboard.nResolved', { n: stats.alerts_resolved }) }}</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-card__header">
              <el-icon :size="28" color="#909399"><Tickets /></el-icon>
              <span class="stat-card__title">{{ t('dashboard.workOrders') }}</span>
            </div>
            <div class="stat-card__values">
              <el-statistic :title="t('dashboard.total')" :value="stats.work_orders_total" />
              <div class="stat-card__breakdown">
                <el-tag size="small">{{ t('dashboard.nOpen', { n: stats.work_orders_open }) }}</el-tag>
                <el-tag type="primary" size="small">{{ t('dashboard.nInProgress', { n: stats.work_orders_in_progress }) }}</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Worker Status Banner -->
      <el-card v-if="workerStatus !== null" shadow="never" class="dashboard-view__worker-card">
        <div class="worker-status">
          <div class="worker-status__indicator">
            <span class="worker-status__dot" :class="workerDotClass" />
            <span class="worker-status__label">{{ workerStatusLabel }}</span>
          </div>
          <div class="worker-status__stats">
            <div class="worker-status__stat">
              <span class="worker-status__stat-label">{{ t('dashboard.workerLastRun') }}</span>
              <span class="worker-status__stat-value">{{ workerLastRun }}</span>
            </div>
            <div class="worker-status__stat">
              <span class="worker-status__stat-label">{{ t('dashboard.workerInspections') }}</span>
              <span class="worker-status__stat-value">{{ workerStatus.total_inspections }}</span>
            </div>
            <div class="worker-status__stat">
              <span class="worker-status__stat-label">{{ t('dashboard.workerSuccessRate') }}</span>
              <span class="worker-status__stat-value">{{ workerSuccessRate }}</span>
            </div>
            <div class="worker-status__stat">
              <span class="worker-status__stat-label">{{ t('dashboard.workerCameras') }}</span>
              <span class="worker-status__stat-value">{{ workerStatus.cameras_active }}</span>
            </div>
            <div class="worker-status__stat">
              <span class="worker-status__stat-label">{{ t('dashboard.workerAvgDuration') }}</span>
              <span class="worker-status__stat-value">{{ Math.round(workerStatus.avg_duration_ms) }}ms</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- Charts Row -->
      <el-row :gutter="16" class="dashboard-view__row">
        <el-col :xs="24" :lg="10">
          <el-card shadow="never" class="dashboard-view__chart-card">
            <template #header>
              <span>{{ t('dashboard.severityPie') }}</span>
            </template>
            <v-chart
              v-if="severityTotal > 0"
              class="dashboard-view__chart"
              :option="severityPieOption"
              autoresize
            />
            <el-empty v-else :description="t('common.empty.noAlertsRecorded')" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="14">
          <el-card shadow="never" class="dashboard-view__chart-card">
            <template #header>
              <span>{{ t('dashboard.alertTrend') }}</span>
            </template>
            <v-chart
              v-if="trendTotal > 0"
              class="dashboard-view__chart"
              :option="trendLineOption"
              autoresize
            />
            <el-empty v-else :description="t('common.empty.noAlertsRecorded')" />
          </el-card>
        </el-col>
      </el-row>

      <!-- Recent Alerts Table -->
      <el-card shadow="never" class="dashboard-view__section">
        <template #header>
          <span>{{ t('dashboard.recentAlerts') }}</span>
        </template>
        <el-table :data="recentAlerts" stripe style="width: 100%" :empty-text="t('common.empty.noAlerts')">
          <el-table-column prop="alert_type" :label="t('common.table.type')" min-width="120" />
          <el-table-column prop="severity" :label="t('common.table.severity')" min-width="100">
            <template #default="{ row }">
              <el-tag :type="severityTagType(row.severity)" size="small" effect="dark">
                {{ t('common.enum.alertSeverity.' + row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.table.status')" min-width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ t('common.enum.alertStatus.' + row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detected_at" :label="t('common.table.detectedAt')" min-width="180">
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
import { useI18n } from 'vue-i18n';
import {
  Loading,
  VideoCamera,
  PictureFilled,
  Bell,
  Tickets,
} from '@element-plus/icons-vue';

import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { PieChart, LineChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';

import { getAlertTrend, getDashboardStats, getWorkerStatus, listAlerts } from '@/api/resources';
import type { Alert, AlertSeverity, AlertStatus, AlertTrendPoint, DashboardStats, WorkerStatus } from '@/api/types';
import { RECENT_ALERTS_COUNT } from '@/utils/constants';

use([CanvasRenderer, PieChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent]);

const { t } = useI18n();

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

const SEVERITY_COLORS: Record<string, string> = {
  low: '#67c23a',
  medium: '#e6a23c',
  high: '#f56c6c',
  critical: '#c45656',
};

const loading = ref(true);
const stats = ref<DashboardStats>({ ...FALLBACK_STATS });
const recentAlerts = ref<Alert[]>([]);
const trendData = ref<AlertTrendPoint[]>([]);
const workerStatus = ref<WorkerStatus | null>(null);

const severityTotal = computed(() =>
  Object.values(stats.value.alerts_by_severity).reduce((sum, n) => sum + n, 0),
);

const trendTotal = computed(() =>
  trendData.value.reduce((sum, p) => sum + p.count, 0),
);

const workerDotClass = computed(() => {
  if (workerStatus.value === null) return 'worker-status__dot--offline';
  const s = workerStatus.value;
  if (s.is_stale || s.status === 'offline') return 'worker-status__dot--stale';
  if (s.status === 'running') return 'worker-status__dot--running';
  if (s.status === 'error') return 'worker-status__dot--error';
  return 'worker-status__dot--stopped';
});

const workerStatusLabel = computed(() => {
  if (workerStatus.value === null) return t('dashboard.workerOffline');
  const s = workerStatus.value;
  if (s.is_stale && s.status === 'running') return t('dashboard.workerStale');
  const keyMap: Record<string, string> = {
    running: 'dashboard.workerRunning',
    stopped: 'dashboard.workerStopped',
    error: 'dashboard.workerError',
    offline: 'dashboard.workerOffline',
    idle: 'dashboard.workerOffline',
  };
  return t(keyMap[s.status] ?? 'dashboard.workerOffline');
});

const workerLastRun = computed(() => {
  if (workerStatus.value === null || workerStatus.value.last_run_at === null) {
    return t('dashboard.workerNever');
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'medium' }).format(
    new Date(workerStatus.value.last_run_at),
  );
});

const workerSuccessRate = computed(() => {
  if (workerStatus.value === null || workerStatus.value.total_inspections === 0) return '—';
  const rate = (workerStatus.value.successful / workerStatus.value.total_inspections) * 100;
  return `${rate.toFixed(1)}%`;
});

// --- ECharts options ---

const severityPieOption = computed(() => {
  const bySev = stats.value.alerts_by_severity;
  const keys = Object.keys(bySev).length > 0 ? Object.keys(bySev) : ['low', 'medium', 'high', 'critical'];
  const data = keys
    .filter((k) => (bySev[k] ?? 0) > 0)
    .map((k) => ({
      name: t('common.enum.alertSeverity.' + k),
      value: bySev[k] ?? 0,
      itemStyle: { color: SEVERITY_COLORS[k] ?? '#909399' },
    }));

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 4, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['38%', '65%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: true,
        label: { show: true, formatter: '{b}\n{c}', fontSize: 12 },
        emphasis: { label: { show: true, fontWeight: 'bold' } },
        data,
      },
    ],
  };
});

const trendLineOption = computed(() => {
  const trendMap = new Map(trendData.value.map((p) => [p.date, p.count]));
  const today = new Date();
  const dates: string[] = [];
  const counts: number[] = [];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setUTCDate(d.getUTCDate() - i);
    const dateStr = d.toISOString().split('T')[0]!;
    dates.push(dateStr.slice(5)); // MM-DD
    counts.push(trendMap.get(dateStr) ?? 0);
  }

  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '6%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'line',
        data: counts,
        smooth: true,
        areaStyle: { opacity: 0.12 },
        lineStyle: { width: 2, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        symbolSize: 6,
      },
    ],
  };
});

// --- Utilities ---

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
    const [statsData, alertsData, trend, ws] = await Promise.all([
      getDashboardStats(),
      listAlerts({ limit: RECENT_ALERTS_COUNT }),
      getAlertTrend(7),
      getWorkerStatus(),
    ]);
    stats.value = statsData;
    recentAlerts.value = alertsData;
    trendData.value = trend;
    workerStatus.value = ws;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : t('dashboard.loadFailed');
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

.dashboard-view__worker-card {
  margin-bottom: 20px;
}

.worker-status {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.worker-status__indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  min-width: 120px;
}

.worker-status__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.worker-status__dot--running { background: #67c23a; box-shadow: 0 0 6px #67c23a88; }
.worker-status__dot--stopped { background: #909399; }
.worker-status__dot--error { background: #f56c6c; }
.worker-status__dot--stale { background: #e6a23c; }
.worker-status__dot--offline { background: #c0c4cc; }

.worker-status__stats {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.worker-status__stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.worker-status__stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.worker-status__stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
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

.dashboard-view__chart-card {
  height: 100%;
}

.dashboard-view__chart {
  width: 100%;
  height: 300px;
}

.dashboard-view__section {
  margin-bottom: 20px;
}
</style>
