<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('camera.title') }}</h2>
        <p class="page-subtitle">{{ t('camera.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">{{ t('common.button.addCamera') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="pagedCameras" row-key="id" stripe>
      <el-table-column prop="id" :label="t('common.table.id')" width="90" />
      <el-table-column prop="name" :label="t('common.table.name')" min-width="180">
        <template #default="{ row }">
          <RouterLink :to="`/cameras/${row.id}`">{{ row.name }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="location" :label="t('common.table.location')" min-width="180" />
      <el-table-column prop="ip" :label="t('common.table.ip')" min-width="150" />
      <el-table-column prop="status" :label="t('common.table.status')" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ t('common.enum.cameraStatus.' + row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.table.actions')" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">{{ t('common.button.config') }}</el-button>
          <el-button size="small" @click="$router.push(`/cameras/${row.id}/scenes`)">{{ t('common.button.scenes') }}</el-button>
          <el-button size="small" @click="$router.push(`/cameras/${row.id}/rules`)">{{ t('common.button.rules') }}</el-button>
          <el-popconfirm
            :title="t('camera.deleteConfirm')"
            :confirm-button-text="t('common.button.delete')"
            :cancel-button-text="t('common.button.cancel')"
            confirm-button-type="danger"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger" :loading="deleteLoading === row.id">{{ t('common.button.delete') }}</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noCameras') }}</span>
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

    <!-- Create / Edit dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? t('camera.editCamera') : t('camera.addCamera')"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" @submit.prevent="handleSubmit">
        <el-form-item :label="t('camera.formName')" required>
          <el-input v-model="form.name" :placeholder="t('camera.phName')" />
        </el-form-item>
        <el-form-item :label="t('camera.formLocation')" required>
          <el-input v-model="form.location" :placeholder="t('camera.phLocation')" />
        </el-form-item>
        <el-form-item :label="t('camera.formIp')" required>
          <el-input v-model="form.ip" :placeholder="t('camera.phIp')" />
        </el-form-item>
        <el-form-item :label="t('camera.formPort')">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="t('camera.formUsername')" required>
          <el-input v-model="form.username" :placeholder="t('camera.phUsername')" />
        </el-form-item>
        <el-form-item :label="t('camera.formPassword')" :required="!isEditing">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEditing ? t('camera.phPasswordKeep') : t('camera.phPassword')"
          />
        </el-form-item>
        <el-form-item :label="t('camera.formStatus')">
          <el-select v-model="form.status">
            <el-option :label="t('common.enum.cameraStatus.active')" value="active" />
            <el-option :label="t('common.enum.cameraStatus.inactive')" value="inactive" />
            <el-option :label="t('common.enum.cameraStatus.maintenance')" value="maintenance" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.button.cancel') }}</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ isEditing ? t('common.button.save') : t('common.button.create') }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { createCamera, deleteCamera, listCameras, updateCamera } from '@/api/cameras';
import type { Camera, CameraStatus, CameraUpdatePayload } from '@/api/types';
import { cameraStatusTagType } from '@/utils/tagType';
import { DEFAULT_CAMERA_PORT, DEFAULT_LIST_LIMIT } from '@/utils/constants';

const { t } = useI18n();

const cameras = ref<Camera[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const dialogVisible = ref(false);
const isEditing = ref(false);
const editingId = ref<number | null>(null);
const submitLoading = ref(false);
const deleteLoading = ref<number | null>(null);

interface CameraForm {
  name: string;
  location: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  status: CameraStatus;
}

const defaultForm = (): CameraForm => ({
  name: '',
  location: '',
  ip: '',
  port: DEFAULT_CAMERA_PORT,
  username: 'admin',
  password: '',
  status: 'active',
});

const form = reactive<CameraForm>(defaultForm());

const pagedCameras = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return cameras.value.slice(start, start + pageSize.value);
});

const statusType = cameraStatusTagType;

function openCreateDialog(): void {
  isEditing.value = false;
  editingId.value = null;
  Object.assign(form, defaultForm());
  dialogVisible.value = true;
}

function openEditDialog(camera: Camera): void {
  isEditing.value = true;
  editingId.value = camera.id;
  form.name = camera.name;
  form.location = camera.location;
  form.ip = camera.ip;
  form.port = camera.port;
  form.username = camera.username ?? 'admin';
  form.password = '';
  form.status = camera.status;
  dialogVisible.value = true;
}

async function handleSubmit(): Promise<void> {
  if (!form.name || !form.location || !form.ip) {
    ElMessage.error(t('camera.toastRequired'));
    return;
  }

  submitLoading.value = true;
  try {
    if (isEditing.value && editingId.value !== null) {
      const payload: CameraUpdatePayload = {
        name: form.name,
        location: form.location,
        ip: form.ip,
        port: form.port,
        username: form.username,
        status: form.status,
      };
      if (form.password) {
        payload.password = form.password;
      }
      await updateCamera(editingId.value, payload);
      ElMessage.success(t('camera.toastUpdated'));
    } else {
      if (!form.username || !form.password) {
        ElMessage.error(t('camera.toastCredsRequired'));
        return;
      }
      await createCamera({
        name: form.name,
        location: form.location,
        ip: form.ip,
        port: form.port,
        username: form.username,
        password: form.password,
        status: form.status,
      });
      ElMessage.success(t('camera.toastCreated'));
    }
    dialogVisible.value = false;
    await loadCameras();
  } catch {
    ElMessage.error(isEditing.value ? t('camera.toastUpdateFailed') : t('camera.toastCreateFailed'));
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(id: number): Promise<void> {
  deleteLoading.value = id;
  try {
    await deleteCamera(id);
    ElMessage.success(t('camera.toastDeleted'));
    await loadCameras();
  } catch {
    ElMessage.error(t('camera.toastDeleteFailed'));
  } finally {
    deleteLoading.value = null;
  }
}

async function loadCameras(): Promise<void> {
  loading.value = true;
  try {
    cameras.value = await listCameras({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error(t('camera.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadCameras();
});
</script>
