<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('scene.title') }}</h2>
        <p class="page-subtitle">{{ t('scene.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">{{ t('common.button.createScene') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="pagedScenes" row-key="id" stripe>
      <el-table-column prop="id" :label="t('common.table.id')" width="90" />
      <el-table-column prop="name" :label="t('common.table.name')" min-width="180">
        <template #default="{ row }">
          <RouterLink :to="`/scenes/${row.id}`">{{ row.name }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="camera_id" :label="t('common.table.cameraId')" width="130" />
      <el-table-column :label="t('common.table.baseline')" min-width="220">
        <template #default="{ row }">{{ row.baseline_image_path ?? t('common.notConfigured') }}</template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noScenes') }}</span>
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
      :title="t('scene.createScene')"
      width="440px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" @submit.prevent="handleCreate">
        <el-form-item :label="t('scene.formName')" required>
          <el-input v-model="form.name" :placeholder="t('scene.phName')" />
        </el-form-item>
        <el-form-item :label="t('scene.formCameraId')" required>
          <el-input-number v-model="form.camera_id" :min="1" controls-position="right" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.button.cancel') }}</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleCreate">{{ t('common.button.create') }}</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { createScene, listScenes } from '@/api/resources';
import type { Scene } from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

const { t } = useI18n();

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
    ElMessage.error(t('scene.toastNameRequired'));
    return;
  }

  submitLoading.value = true;
  try {
    await createScene({ camera_id: form.camera_id, name: form.name });
    ElMessage.success(t('scene.toastCreated'));
    dialogVisible.value = false;
    await loadScenes();
  } catch {
    ElMessage.error(t('scene.toastCreateFailed'));
  } finally {
    submitLoading.value = false;
  }
}

async function loadScenes(): Promise<void> {
  loading.value = true;
  try {
    scenes.value = await listScenes({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error(t('scene.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadScenes();
});
</script>
