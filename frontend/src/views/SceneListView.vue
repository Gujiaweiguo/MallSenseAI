<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">Scenes</h2>
        <p class="page-subtitle">Scene list for all cameras.</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">Create Scene</el-button>
    </div>

    <el-table v-loading="loading" :data="pagedScenes" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="name" label="Name" min-width="180">
        <template #default="{ row }">
          <RouterLink :to="`/scenes/${row.id}`">{{ row.name }}</RouterLink>
        </template>
      </el-table-column>
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

    <!-- Create Scene dialog -->
    <el-dialog
      v-model="dialogVisible"
      title="Create Scene"
      width="440px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" @submit.prevent="handleCreate">
        <el-form-item label="Name" required>
          <el-input v-model="form.name" placeholder="Scene name" />
        </el-form-item>
        <el-form-item label="Camera ID" required>
          <el-input-number v-model="form.camera_id" :min="1" controls-position="right" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleCreate">Create</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';

import { createScene, listScenes } from '@/api/resources';
import type { Scene } from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

const scenes = ref<Scene[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const dialogVisible = ref(false);
const submitLoading = ref(false);

interface SceneForm {
  name: string;
  camera_id: number;
}

const defaultForm = (): SceneForm => ({ name: '', camera_id: 1 });
const form = reactive<SceneForm>(defaultForm());

const pagedScenes = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return scenes.value.slice(start, start + pageSize.value);
});

function openCreateDialog(): void {
  Object.assign(form, defaultForm());
  dialogVisible.value = true;
}

async function handleCreate(): Promise<void> {
  if (!form.name) {
    ElMessage.error('Scene name is required.');
    return;
  }

  submitLoading.value = true;
  try {
    await createScene({ camera_id: form.camera_id, name: form.name });
    ElMessage.success('Scene created.');
    dialogVisible.value = false;
    await loadScenes();
  } catch {
    ElMessage.error('Failed to create scene.');
  } finally {
    submitLoading.value = false;
  }
}

async function loadScenes(): Promise<void> {
  loading.value = true;
  try {
    scenes.value = await listScenes({ limit: DEFAULT_LIST_LIMIT });
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
