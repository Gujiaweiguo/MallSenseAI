<template>
  <section class="page-card">
    <h2 class="page-title">Camera Detail</h2>
    <p class="page-subtitle">Read-only camera details. Editing will be added in a later task.</p>

    <el-skeleton v-if="loading" :rows="5" animated />
    <el-descriptions v-else-if="camera" :column="2" border>
      <el-descriptions-item label="ID">{{ camera.id }}</el-descriptions-item>
      <el-descriptions-item label="Name">{{ camera.name }}</el-descriptions-item>
      <el-descriptions-item label="Location">{{ camera.location }}</el-descriptions-item>
      <el-descriptions-item label="IP">{{ camera.ip }}</el-descriptions-item>
      <el-descriptions-item label="Port">{{ camera.port }}</el-descriptions-item>
      <el-descriptions-item label="Status">{{ camera.status }}</el-descriptions-item>
      <el-descriptions-item label="Created">{{ camera.created_at }}</el-descriptions-item>
      <el-descriptions-item label="Updated">{{ camera.updated_at }}</el-descriptions-item>
    </el-descriptions>
    <el-empty v-else description="Camera not found" />
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { getCamera } from '@/api/cameras';
import type { Camera } from '@/api/types';

const route = useRoute();
const camera = ref<Camera | null>(null);
const loading = ref(false);

async function loadCamera(): Promise<void> {
  const id = Number(route.params.id);
  if (!Number.isInteger(id)) {
    ElMessage.error('Invalid camera ID.');
    return;
  }

  loading.value = true;
  try {
    camera.value = await getCamera(id);
  } catch {
    ElMessage.error('Failed to load camera details.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadCamera();
});
</script>
