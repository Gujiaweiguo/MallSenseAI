<template>
  <section class="page-card">
    <h2 class="page-title">Cameras</h2>
    <p class="page-subtitle">Camera inventory loaded from GET /api/cameras.</p>

    <el-table v-loading="loading" :data="pagedCameras" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="name" label="Name" min-width="180">
        <template #default="{ row }">
          <RouterLink :to="`/cameras/${row.id}`">{{ row.name }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="Location" min-width="180" />
      <el-table-column prop="ip" label="IP" min-width="150" />
      <el-table-column prop="status" label="Status" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No cameras found.</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="cameras.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import { listCameras } from '@/api/cameras';
import type { Camera } from '@/api/types';

const cameras = ref<Camera[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const pagedCameras = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return cameras.value.slice(start, start + pageSize.value);
});

function statusType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  if (status === 'active') {
    return 'success';
  }
  if (status === 'maintenance') {
    return 'warning';
  }
  if (status === 'inactive') {
    return 'info';
  }
  return 'danger';
}

async function loadCameras(): Promise<void> {
  loading.value = true;
  try {
    cameras.value = await listCameras({ limit: 100 });
  } catch {
    ElMessage.error('Failed to load cameras.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadCameras();
});
</script>
