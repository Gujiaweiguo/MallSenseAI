<template>
  <section class="page-card">
    <h2 class="page-title">Work Orders</h2>
    <p class="page-subtitle">Work-order list loaded from GET /api/work-orders.</p>

    <el-table v-loading="loading" :data="pagedWorkOrders" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="alert_id" label="Alert ID" width="120" />
      <el-table-column prop="status" label="Status" width="160">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Assigned To" width="150">
        <template #default="{ row }">{{ row.assigned_to ?? 'Unassigned' }}</template>
      </el-table-column>
      <el-table-column prop="notes" label="Notes" min-width="220" show-overflow-tooltip />
      <template #empty>
        <span class="empty-note">No work orders found.</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="workOrders.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import { listWorkOrders } from '@/api/resources';
import type { WorkOrder } from '@/api/types';

const workOrders = ref<WorkOrder[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const pagedWorkOrders = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return workOrders.value.slice(start, start + pageSize.value);
});

function statusType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  if (status === 'closed') {
    return 'success';
  }
  if (status === 'in_progress') {
    return 'warning';
  }
  if (status === 'open') {
    return 'info';
  }
  return 'danger';
}

async function loadWorkOrders(): Promise<void> {
  loading.value = true;
  try {
    workOrders.value = await listWorkOrders({ limit: 100 });
  } catch {
    ElMessage.error('Failed to load work orders.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadWorkOrders();
});
</script>
