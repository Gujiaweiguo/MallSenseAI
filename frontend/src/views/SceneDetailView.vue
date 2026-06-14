<template>
  <section class="page-card scene-detail">
    <el-page-header :icon="null" @back="goBackToCamera">
      <template #content>
        <span class="scene-detail__breadcrumb">{{ t('scene.detailTitle') }}</span>
      </template>
    </el-page-header>
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
          :editing-roi-id="editingRoiId"
          @roi-created="savePolygon"
          @roi-updated="handleRoiUpdated"
          @roi-deleted="handleRoiDeleted"
        />
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card shadow="never">
          <template #header>
            <div class="panel-header">
              <span>{{ t('roi.title') }}</span>
              <div class="panel-header__actions">
                <el-button v-if="editingRoiId !== null" type="warning" size="small" @click="cancelRedraw">
                  {{ t('roi.cancelRedraw') }}
                </el-button>
                <el-button v-else :type="drawingEnabled ? 'warning' : 'primary'" size="small" @click="toggleDrawing">
                  {{ drawingEnabled ? t('common.button.cancelCreate') : t('common.button.createRoi') }}
                </el-button>
              </div>
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

          <el-alert
            v-if="editingRoiId !== null"
            class="scene-detail__draw-alert"
            :title="t('roi.redrawHint')"
            type="warning"
            show-icon
            :closable="false"
          />

          <el-table :data="rois" row-key="id" stripe>
            <el-table-column prop="name" :label="t('common.table.name')" min-width="120" />
            <el-table-column :label="t('common.table.points')" width="80">
              <template #default="{ row }">{{ row.geometry.points.length }}</template>
            </el-table-column>
            <el-table-column :label="t('common.table.actions')" width="160">
              <template #default="{ row }">
                <el-button type="primary" link @click="startRenameRoi(row.id, row.name)">{{ t('common.button.edit') }}</el-button>
                <el-button type="warning" link :disabled="editingRoiId !== null" @click="startRedrawRoi(row.id)">{{ t('roi.redraw') }}</el-button>
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
import { useRoute, useRouter } from 'vue-router';

import type { Roi, RoiGeometry, Scene } from '@/api/types';
import RoiCanvas from '@/components/RoiCanvas.vue';
import { createRoi, deleteRoi, getScene, listRois, triggerSnapshot, updateRoi, updateSceneBaseline } from '@/api/resources';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const scene = ref<Scene | null>(null);
const rois = ref<Roi[]>([]);
const loading = ref(false);
const drawingEnabled = ref(false);
const editingRoiId = ref<number | null>(null);
const snapshotLoading = ref(false);

const sceneId = computed(() => Number(route.params.id));
const baselineUrl = computed(() => {
  if (scene.value === null || !scene.value.baseline_image_path) {
    return null;
  }
  return `/api/scenes/${scene.value.id}/baseline`;
});

function goBackToCamera(): void {
  if (scene.value !== null) {
    void router.push(`/cameras/${scene.value.camera_id}`);
  } else {
    void router.push('/cameras');
  }
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
    if (editingRoiId.value === roiId) {
      editingRoiId.value = null;
    }
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

function startRedrawRoi(roiId: number): void {
  drawingEnabled.value = false;
  editingRoiId.value = roiId;
}

function cancelRedraw(): void {
  editingRoiId.value = null;
}

async function handleRoiUpdated(roiId: number, geometry: RoiGeometry): Promise<void> {
  try {
    const updated = await updateRoi(roiId, { geometry });
    const index = rois.value.findIndex((item) => item.id === roiId);
    if (index !== -1) {
      rois.value[index] = updated;
    }
    editingRoiId.value = null;
    ElMessage.success(t('roi.toastUpdated'));
  } catch {
    ElMessage.error(t('roi.toastUpdateFailed'));
  }
}

async function startRenameRoi(roiId: number, currentName: string): Promise<void> {
  try {
    const result = await ElMessageBox.prompt(t('roi.promptRename'), t('roi.promptRenameTitle'), {
      confirmButtonText: t('common.button.save'),
      cancelButtonText: t('common.button.cancel'),
      inputValue: currentName,
      inputPattern: /\S+/,
      inputErrorMessage: t('roi.nameRequired'),
    });
    const updated = await updateRoi(roiId, { name: result.value });
    const index = rois.value.findIndex((item) => item.id === roiId);
    if (index !== -1) {
      rois.value[index] = updated;
    }
    ElMessage.success(t('roi.toastUpdated'));
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('roi.toastUpdateFailed'));
  }
}

async function captureSnapshot(): Promise<void> {
  if (scene.value === null) {
    return;
  }
  snapshotLoading.value = true;
  try {
    scene.value = await triggerSnapshot(scene.value.id);
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

.panel-header__actions {
  display: flex;
  gap: 8px;
}
</style>
