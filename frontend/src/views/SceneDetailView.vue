<template>
  <section class="page-card scene-detail">
    <div class="scene-detail__header">
      <div>
        <h2 class="page-title">Scene Detail</h2>
        <p class="page-subtitle">Manage baseline image and polygon ROIs.</p>
      </div>
      <div class="scene-detail__actions">
        <el-upload :show-file-list="false" :before-upload="uploadBaseline" accept="image/*">
          <el-button type="primary">Upload Baseline</el-button>
        </el-upload>
        <el-button :loading="snapshotLoading" @click="captureSnapshot">Trigger Snapshot</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-empty v-else-if="scene === null" description="Scene not found" />
    <el-row v-else :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-descriptions :column="2" border class="scene-detail__info">
          <el-descriptions-item label="ID">{{ scene.id }}</el-descriptions-item>
          <el-descriptions-item label="Name">{{ scene.name }}</el-descriptions-item>
          <el-descriptions-item label="Camera ID">{{ scene.camera_id }}</el-descriptions-item>
          <el-descriptions-item label="Baseline">{{ scene.baseline_image_path ?? 'Not configured' }}</el-descriptions-item>
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
              <span>ROIs</span>
              <el-button :type="drawingEnabled ? 'warning' : 'primary'" size="small" @click="toggleDrawing">
                {{ drawingEnabled ? 'Cancel Create' : 'Create ROI' }}
              </el-button>
            </div>
          </template>

          <el-alert
            v-if="drawingEnabled"
            class="scene-detail__draw-alert"
            title="Click points on the image, then double-click to close the polygon."
            type="info"
            show-icon
            :closable="false"
          />

          <el-table :data="rois" row-key="id" stripe>
            <el-table-column prop="name" label="Name" min-width="120" />
            <el-table-column label="Points" width="80">
              <template #default="{ row }">{{ row.geometry.points.length }}</template>
            </el-table-column>
            <el-table-column label="Actions" width="90">
              <template #default="{ row }">
                <el-button type="danger" link @click="confirmDeleteRoi(row.id, row.name)">Delete</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <span class="empty-note">No ROIs yet.</span>
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
import { useRoute } from 'vue-router';

import type { Roi, RoiGeometry, Scene } from '@/api/types';
import RoiCanvas from '@/components/RoiCanvas.vue';
import { createRoi, deleteRoi, getScene, listRois, triggerSnapshot, updateSceneBaseline } from '@/api/resources';

const route = useRoute();
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
    ElMessage.error('Invalid scene ID.');
    return;
  }

  loading.value = true;
  try {
    const [sceneData, roiData] = await Promise.all([getScene(sceneId.value), listRois(sceneId.value)]);
    scene.value = sceneData;
    rois.value = roiData;
  } catch {
    ElMessage.error('Failed to load scene.');
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
    ElMessage.success('Baseline image updated.');
  } catch {
    ElMessage.error('Failed to upload baseline image.');
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
    const result = await ElMessageBox.prompt('Enter ROI name', 'Create ROI', {
      confirmButtonText: 'Create',
      cancelButtonText: 'Cancel',
      inputPattern: /\S+/,
      inputErrorMessage: 'ROI name is required.',
    });
    const roi = await createRoi(scene.value.id, { name: result.value, geometry });
    rois.value.push(roi);
    drawingEnabled.value = false;
    ElMessage.success('ROI created.');
  } catch (error: unknown) {
    if (error instanceof Error) {
      ElMessage.error('Failed to create ROI.');
    }
  }
}

async function confirmDeleteRoi(roiId: number, roiName: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`Delete ROI "${roiName}"?`, 'Delete ROI', { type: 'warning' });
    await deleteRoi(roiId);
    rois.value = rois.value.filter((item) => item.id !== roiId);
    ElMessage.success('ROI deleted.');
  } catch (error: unknown) {
    if (error instanceof Error) {
      ElMessage.error('Failed to delete ROI.');
    }
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
    ElMessage.success('Snapshot triggered.');
  } catch {
    ElMessage.error('Failed to trigger snapshot.');
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
