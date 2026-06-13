<template>
  <section class="page-card scene-detail">
    <div class="scene-detail__header">
      <div>
        <h2 class="page-title">{{ t('scene.detailTitle') }}</h2>
        <p class="page-subtitle">{{ t('scene.detailSubtitle') }}</p>
      </div>
      <div class="scene-detail__actions">
        <el-upload :show-file-list="false" :before-upload="uploadBaseline" accept="image/*">
          <el-button type="primary">{{ t('common.button.uploadBaseline') }}</el-button>
        </el-upload>
        <el-button :loading="snapshotLoading" @click="captureSnapshot">{{ t('common.button.triggerSnapshot') }}</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-empty v-else-if="scene === null" :description="t('common.empty.sceneNotFound')" />
    <el-row v-else :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-descriptions :column="2" border class="scene-detail__info">
          <el-descriptions-item :label="t('common.table.id')">{{ scene.id }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.table.name')">{{ scene.name }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.table.cameraId')">{{ scene.camera_id }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.table.baseline')">{{ scene.baseline_image_path ?? t('common.notConfigured') }}</el-descriptions-item>
        </el-descriptions>

        <RoiCanvas
          :rois="rois"
          :image-url="baselineUrl"
          :editable="drawingEnabled"
          @roi-created="savePolygon"
          @roi-deleted="handleRoiDeleted"
        />
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card shadow="never">
          <template #header>
            <div class="panel-header">
              <span>{{ t('roi.title') }}</span>
              <el-button :type="drawingEnabled ? 'warning' : 'primary'" size="small" @click="toggleDrawing">
                {{ drawingEnabled ? t('common.button.cancelCreate') : t('common.button.createRoi') }}
              </el-button>
            </div>
          </template>

          <el-alert
            v-if="drawingEnabled"
            class="scene-detail__draw-alert"
            :title="t('roi.hint')"
            type="info"
            show-icon
            :closable="false"
          />

          <el-table :data="rois" row-key="id" stripe>
            <el-table-column prop="name" :label="t('common.table.name')" min-width="120" />
            <el-table-column :label="t('common.table.points')" width="80">
              <template #default="{ row }">{{ row.geometry.points.length }}</template>
            </el-table-column>
            <el-table-column :label="t('common.table.actions')" width="90">
              <template #default="{ row }">
                <el-button type="danger" link @click="confirmDeleteRoi(row.id, row.name)">{{ t('common.button.delete') }}</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <span class="empty-note">{{ t('common.empty.noRois') }}</span>
            </template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import type { UploadRawFile } from 'element-plus';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import type { Roi, RoiGeometry, Scene } from '@/api/types';
import RoiCanvas from '@/components/RoiCanvas.vue';
import { createRoi, deleteRoi, getScene, listRois, triggerSnapshot, updateSceneBaseline } from '@/api/resources';

const route = useRoute();
const { t } = useI18n();
const scene = ref<Scene | null>(null);
const rois = ref<Roi[]>([]);
const loading = ref(false);
const drawingEnabled = ref(false);
const snapshotLoading = ref(false);

const sceneId = computed(() => Number(route.params.id));
const baselineUrl = computed(() => normalizeImageUrl(scene.value?.baseline_image_path ?? null));

function normalizeImageUrl(path: string | null): string | null {
  if (path === null || path.length === 0) {
    return null;
  }
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('/')) {
    return path;
  }
  return `/api/${path}`;
}

async function loadScene(): Promise<void> {
  if (!Number.isInteger(sceneId.value)) {
    ElMessage.error(t('scene.toastInvalidId'));
    return;
  }

  loading.value = true;
  try {
    const [sceneData, roiData] = await Promise.all([getScene(sceneId.value), listRois(sceneId.value)]);
    scene.value = sceneData;
    rois.value = roiData;
  } catch {
    ElMessage.error(t('scene.toastLoadFailedScene'));
  } finally {
    loading.value = false;
  }
}

async function uploadBaseline(file: UploadRawFile): Promise<boolean> {
  if (scene.value === null) {
    return false;
  }
  try {
    scene.value = await updateSceneBaseline(scene.value.id, file);
    ElMessage.success(t('scene.toastBaselineUpdated'));
  } catch {
    ElMessage.error(t('scene.toastBaselineFailed'));
  }
  return false;
}

function toggleDrawing(): void {
  drawingEnabled.value = !drawingEnabled.value;
}

async function savePolygon(geometry: RoiGeometry): Promise<void> {
  if (scene.value === null) {
    return;
  }
  try {
    const result = await ElMessageBox.prompt(t('roi.promptName'), t('roi.promptCreate'), {
      confirmButtonText: t('common.button.create'),
      cancelButtonText: t('common.button.cancel'),
      inputPattern: /\S+/,
      inputErrorMessage: t('roi.nameRequired'),
    });
    const roi = await createRoi(scene.value.id, { name: result.value, geometry });
    rois.value.push(roi);
    drawingEnabled.value = false;
    ElMessage.success(t('roi.toastCreated'));
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('roi.toastCreateFailed'));
  }
}

async function confirmDeleteRoi(roiId: number, roiName: string): Promise<void> {
  try {
    await ElMessageBox.confirm(t('roi.deleteConfirm', { name: roiName }), t('roi.deleteTitle'), { type: 'warning' });
    await deleteRoi(roiId);
    rois.value = rois.value.filter((item) => item.id !== roiId);
    ElMessage.success(t('roi.toastDeleted'));
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('roi.toastDeleteFailed'));
  }
}

function handleRoiDeleted(roiId: number): void {
  const roi = rois.value.find((item) => item.id === roiId);
  if (roi) {
    void confirmDeleteRoi(roiId, roi.name);
  }
}

async function captureSnapshot(): Promise<void> {
  if (scene.value === null) {
    return;
  }
  snapshotLoading.value = true;
  try {
    scene.value = await triggerSnapshot(scene.value.camera_id);
    ElMessage.success(t('scene.toastSnapshotTriggered'));
  } catch {
    ElMessage.error(t('scene.toastSnapshotFailed'));
  } finally {
    snapshotLoading.value = false;
  }
}

onMounted(() => {
  void loadScene();
});
</script>

<style scoped>
.scene-detail__header,
.scene-detail__actions,
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.scene-detail__actions {
  flex-wrap: wrap;
}

.scene-detail__info {
  margin-bottom: 16px;
}

.scene-detail__draw-alert {
  margin-bottom: 12px;
}
</style>
