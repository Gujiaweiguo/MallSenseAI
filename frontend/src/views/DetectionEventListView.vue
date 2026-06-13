<template>
  <section class="page-card">
    <h2 class="page-title">{{ t('detection.title') }}</h2>
    <p class="page-subtitle">{{ t('detection.subtitle') }}</p>

    <div class="filter-bar">
      <el-input-number
        v-model="cameraIdFilter"
        :placeholder="t('detection.phCameraId')"
        :min="1"
        controls-position="right"
        style="width: 180px"
        @change="currentPage = 1"
      />
      <el-select v-model="detectorTypeFilter" :placeholder="t('detection.phDetectorType')" clearable style="width: 200px" @change="currentPage = 1">
        <el-option :label="t('common.all')" value="" />
        <el-option :label="t('common.enum.detectorType.yolo')" value="yolo" />
        <el-option :label="t('common.enum.detectorType.image_compare')" value="image_compare" />
        <el-option :label="t('common.enum.detectorType.blue_box')" value="blue_box" />
      </el-select>
      <el-button :loading="exporting" style="margin-left: auto" @click="handleExport">{{ t('common.button.export') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="pagedEvents" row-key="id" stripe @row-click="handleRowClick">
      <el-table-column prop="id" :label="t('common.table.id')" width="90" />
      <el-table-column prop="camera_id" :label="t('common.table.cameraId')" width="110" />
      <el-table-column :label="t('common.table.roiId')" width="110">
        <template #default="{ row }">{{ row.roi_id ?? t('common.na') }}</template>
      </el-table-column>
      <el-table-column :label="t('common.table.detectorType')" min-width="160">
        <template #default="{ row }">{{ t('common.enum.detectorType.' + row.detector_type) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.table.confidence')" width="130">
        <template #default="{ row }">{{ formatConfidence(row.confidence) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.table.detectedAt')" min-width="190">
        <template #default="{ row }">{{ formatDate(row.detected_at) }}</template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noDetectionEvents') }}</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredEvents.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="t('detection.metadataTitle')" width="720px" destroy-on-close>
      <template v-if="selectedEvent !== null">
        <div class="detection-events__meta-grid">
          <div v-for="entry in metadataEntries" :key="entry.key" class="detection-events__meta-row">
            <span class="detection-events__meta-key">{{ entry.key }}</span>
            <pre class="detection-events__meta-value">{{ entry.value }}</pre>
          </div>
          <span v-if="metadataEntries.length === 0" class="empty-note">{{ t('common.empty.noEventMetadata') }}</span>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { exportDetectionEvents, listDetectionEvents } from '@/api/resources';
import type { DetectionEvent, DetectorType } from '@/api/types';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

const { t } = useI18n();
const events = ref<DetectionEvent[]>([]);
const loading = ref(false);
const exporting = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);
const cameraIdFilter = ref<number | undefined>();
const detectorTypeFilter = ref<DetectorType | ''>('');
const dialogVisible = ref(false);
const selectedEvent = ref<DetectionEvent | null>(null);

const filteredEvents = computed(() => {
  let result = events.value;
  if (cameraIdFilter.value !== undefined) {
    result = result.filter((event) => event.camera_id === cameraIdFilter.value);
  }
  if (detectorTypeFilter.value) {
    result = result.filter((event) => event.detector_type === detectorTypeFilter.value);
  }
  return result;
});

const pagedEvents = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredEvents.value.slice(start, start + pageSize.value);
});

const metadataEntries = computed(() => {
  if (selectedEvent.value === null) return [];
  return Object.entries(selectedEvent.value.event_metadata).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }));
});

function formatConfidence(value: number | null): string {
  if (value === null) return t('common.na');
  return `${(value * 100).toFixed(1)}%`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function handleRowClick(row: DetectionEvent): void {
  selectedEvent.value = row;
  dialogVisible.value = true;
}

async function loadEvents(): Promise<void> {
  loading.value = true;
  try {
    events.value = await listDetectionEvents({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error(t('detection.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

async function handleExport(): Promise<void> {
  exporting.value = true;
  try {
    const blob = await exportDetectionEvents(
      cameraIdFilter.value !== undefined ? { camera_id: cameraIdFilter.value } : {},
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'detection_events.csv';
    link.click();
    URL.revokeObjectURL(url);
    ElMessage.success(t('detection.toastExported'));
  } catch {
    ElMessage.error(t('detection.toastExportFailed'));
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  void loadEvents();
});
</script>

<style scoped>
.detection-events__meta-grid {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
}

.detection-events__meta-row {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-2);
  padding: var(--ms-space-3);
  background: #f8fafc;
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-1);
}

.detection-events__meta-key {
  color: var(--ms-color-muted);
  font-size: 13px;
  font-weight: 600;
}

.detection-events__meta-value {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
