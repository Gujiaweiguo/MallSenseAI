<template>
  <section class="page-card">
    <h2 class="page-title">Scenes</h2>
    <p class="page-subtitle">Read-only scene list. ROI and baseline editing are reserved for T10.</p>

    <el-table v-loading="loading" :data="pagedScenes" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="name" label="Name" min-width="180" />
      <el-table-column prop="camera_id" label="Camera ID" width="130" />
      <el-table-column label="Baseline" min-width="220">
        <template #default="{ row }">{{ row.baseline_image_path ?? 'Not configured' }}</template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No scenes found.</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="scenes.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import { listScenes } from '@/api/resources';
import type { Scene } from '@/api/types';

const scenes = ref<Scene[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const pagedScenes = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return scenes.value.slice(start, start + pageSize.value);
});

async function loadScenes(): Promise<void> {
  loading.value = true;
  try {
    scenes.value = await listScenes({ limit: 100 });
  } catch {
    ElMessage.error('Failed to load scenes.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadScenes();
});
</script>
