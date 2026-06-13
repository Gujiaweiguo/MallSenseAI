<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('camera.detailTitle') }}</h2>
        <p class="page-subtitle">{{ t('camera.detailSubtitle') }}</p>
      </div>
      <div v-if="camera" class="detail-actions">
        <el-button v-if="!editing" type="primary" @click="startEditing">{{ t('common.button.edit') }}</el-button>
        <template v-else>
          <el-button @click="cancelEditing">{{ t('common.button.cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">{{ t('common.button.save') }}</el-button>
        </template>
        <el-popconfirm
          :title="t('camera.deleteConfirm')"
          :confirm-button-text="t('common.button.delete')"
          :cancel-button-text="t('common.button.cancel')"
          confirm-button-type="danger"
          @confirm="handleDelete"
        >
          <template #reference>
            <el-button type="danger" :loading="deleting">{{ t('common.button.delete') }}</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="5" animated />

    <!-- Read mode -->
    <el-descriptions v-else-if="camera && !editing" :column="2" border>
      <el-descriptions-item :label="t('common.table.id')">{{ camera.id }}</el-descriptions-item>
      <el-descriptions-item :label="t('common.table.name')">{{ camera.name }}</el-descriptions-item>
      <el-descriptions-item :label="t('common.table.location')">{{ camera.location }}</el-descriptions-item>
      <el-descriptions-item :label="t('common.table.ip')">{{ camera.ip }}</el-descriptions-item>
      <el-descriptions-item :label="t('common.table.port')">{{ camera.port }}</el-descriptions-item>
      <el-descriptions-item :label="t('common.table.status')">
        <el-tag :type="statusType(camera.status)">{{ t('common.enum.cameraStatus.' + camera.status) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item :label="t('camera.created')">{{ camera.created_at }}</el-descriptions-item>
      <el-descriptions-item :label="t('camera.updated')">{{ camera.updated_at }}</el-descriptions-item>
    </el-descriptions>

    <!-- Edit mode -->
    <el-form v-else-if="camera && editing" :model="editForm" label-width="100px" style="max-width: 600px">
      <el-form-item :label="t('camera.formName')" required>
        <el-input v-model="editForm.name" />
      </el-form-item>
      <el-form-item :label="t('camera.formLocation')" required>
        <el-input v-model="editForm.location" />
      </el-form-item>
      <el-form-item :label="t('camera.formIp')" required>
        <el-input v-model="editForm.ip" />
      </el-form-item>
      <el-form-item :label="t('camera.formPort')">
        <el-input-number v-model="editForm.port" :min="1" :max="65535" />
      </el-form-item>
      <el-form-item :label="t('camera.formStatus')">
        <el-select v-model="editForm.status">
          <el-option :label="t('common.enum.cameraStatus.active')" value="active" />
          <el-option :label="t('common.enum.cameraStatus.inactive')" value="inactive" />
          <el-option :label="t('common.enum.cameraStatus.maintenance')" value="maintenance" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-empty v-else :description="t('common.empty.cameraNotFound')" />

    <!-- Related links -->
    <div v-if="camera" class="related-links">
      <h3>{{ t('common.related') }}</h3>
      <ul>
        <li><RouterLink :to="`/scenes?camera_id=${camera.id}`">{{ t('camera.scenesForCamera') }}</RouterLink></li>
        <li><RouterLink :to="`/cameras/${camera.id}/rules`">{{ t('camera.rulesForCamera') }}</RouterLink></li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { deleteCamera, getCamera, updateCamera } from '@/api/cameras';
import type { Camera, CameraStatus } from '@/api/types';
import { cameraStatusTagType } from '@/utils/tagType';
import { DEFAULT_CAMERA_PORT } from '@/utils/constants';

const { t } = useI18n();

const route = useRoute();
const router = useRouter();

const camera = ref<Camera | null>(null);
const loading = ref(false);
const editing = ref(false);
const saving = ref(false);
const deleting = ref(false);

interface EditForm {
  name: string;
  location: string;
  ip: string;
  port: number;
  status: CameraStatus;
}

const editForm = reactive<EditForm>({
  name: '',
  location: '',
  ip: '',
  port: DEFAULT_CAMERA_PORT,
  status: 'active',
});

const statusType = cameraStatusTagType;

function startEditing(): void {
  if (!camera.value) return;
  editForm.name = camera.value.name;
  editForm.location = camera.value.location;
  editForm.ip = camera.value.ip;
  editForm.port = camera.value.port;
  editForm.status = camera.value.status;
  editing.value = true;
}

function cancelEditing(): void {
  editing.value = false;
}

async function handleSave(): Promise<void> {
  if (!camera.value) return;
  if (!editForm.name || !editForm.location || !editForm.ip) {
    ElMessage.error(t('camera.toastRequired'));
    return;
  }

  saving.value = true;
  try {
    camera.value = await updateCamera(camera.value.id, {
      name: editForm.name,
      location: editForm.location,
      ip: editForm.ip,
      port: editForm.port,
      status: editForm.status,
    });
    editing.value = false;
    ElMessage.success(t('camera.toastUpdated'));
  } catch {
    ElMessage.error(t('camera.toastUpdateFailed'));
  } finally {
    saving.value = false;
  }
}

async function handleDelete(): Promise<void> {
  if (!camera.value) return;
  deleting.value = true;
  try {
    await deleteCamera(camera.value.id);
    ElMessage.success(t('camera.toastDeleted'));
    void router.push('/cameras');
  } catch {
    ElMessage.error(t('camera.toastDeleteFailed'));
  } finally {
    deleting.value = false;
  }
}

async function loadCamera(): Promise<void> {
  const id = Number(route.params.id);
  if (!Number.isInteger(id)) {
    ElMessage.error(t('camera.toastInvalidId'));
    return;
  }

  loading.value = true;
  try {
    camera.value = await getCamera(id);
  } catch {
    ElMessage.error(t('camera.toastDetailFailed'));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadCamera();
});
</script>

<style scoped>
.detail-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.related-links {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.related-links h3 {
  font-size: 16px;
  margin-bottom: 8px;
}

.related-links ul {
  list-style: none;
  padding: 0;
}

.related-links li {
  margin-bottom: 6px;
}
</style>
