<template>
  <section class="page-card">
    <h2 class="page-title">Alerts</h2>
    <p class="page-subtitle">Alert center loaded from GET /api/alerts.</p>

    <el-table v-loading="loading" :data="pagedAlerts" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="camera_id" label="Camera" width="110" />
      <el-table-column prop="alert_type" label="Type" min-width="180" />
      <el-table-column prop="severity" label="Severity" width="130">
        <template #default="{ row }">
          <el-tag :type="severityType(row.severity)">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="150" />
      <el-table-column label="Detected At" min-width="190">
        <template #default="{ row }">{{ formatDate(row.detected_at) }}</template>
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
        :total="alerts.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import { listAlerts } from '@/api/resources';
import type { Alert } from '@/api/types';

const alerts = ref<Alert[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const pagedAlerts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return alerts.value.slice(start, start + pageSize.value);
});

function severityType(severity: string): 'success' | 'warning' | 'info' | 'danger' {
  if (severity === 'critical' || severity === 'high') {
    return 'danger';
  }
  if (severity === 'medium') {
    return 'warning';
  }
  if (severity === 'low') {
    return 'success';
  }
  return 'info';
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

async function loadAlerts(): Promise<void> {
  loading.value = true;
  try {
    alerts.value = await listAlerts({ limit: 100 });
  } catch {
    ElMessage.error('Failed to load alerts.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadAlerts();
});
</script>
