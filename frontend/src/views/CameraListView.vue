<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">Cameras</h2>
        <p class="page-subtitle">Camera inventory loaded from GET /api/cameras.</p>
      </div>
      <el-button type="primary" @click="openCreateDialog">Add Camera</el-button>
    </div>

    <el-table v-loading="loading" :data="pagedCameras" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="name" label="Name" min-width="180">
        <template #default="{ row }">
          <RouterLink :to="`/cameras/${row.id}`">{{ row.name }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="Location" min-width="180" />
      <el-table-column prop="ip" label="IP" min-width="150" />
      <el-table-column prop="status" label="Status" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">Edit</el-button>
          <el-popconfirm
            title="Delete this camera?"
            confirm-button-text="Delete"
            cancel-button-text="Cancel"
            confirm-button-type="danger"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger" :loading="deleteLoading === row.id">Delete</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No cameras found.</span>
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
      :title="isEditing ? 'Edit Camera' : 'Add Camera'"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" @submit.prevent="handleSubmit">
        <el-form-item label="Name" required>
          <el-input v-model="form.name" placeholder="Camera name" />
        </el-form-item>
        <el-form-item label="Location" required>
          <el-input v-model="form.location" placeholder="e.g. 1F East Corridor" />
        </el-form-item>
        <el-form-item label="IP" required>
          <el-input v-model="form.ip" placeholder="192.168.1.100" />
        </el-form-item>
        <el-form-item label="Port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="Username" required>
          <el-input v-model="form.username" placeholder="Camera HTTP auth username" />
        </el-form-item>
        <el-form-item :label="isEditing ? 'Password' : 'Password'" :required="!isEditing">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEditing ? 'Leave blank to keep current' : 'Camera HTTP auth password'" />
        </el-form-item>
        <el-form-item label="Status">
          <el-select v-model="form.status">
            <el-option label="Active" value="active" />
            <el-option label="Inactive" value="inactive" />
            <el-option label="Maintenance" value="maintenance" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          {{ isEditing ? 'Save' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';

import { createCamera, deleteCamera, listCameras, updateCamera } from '@/api/cameras';
import type { Camera, CameraStatus } from '@/api/types';

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
  port: 80,
  username: 'admin',
  password: '',
  status: 'active',
});

const form = reactive<CameraForm>(defaultForm());

const pagedCameras = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return cameras.value.slice(start, start + pageSize.value);
});

function statusType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  if (status === 'active') return 'success';
  if (status === 'maintenance') return 'warning';
  if (status === 'inactive') return 'info';
  return 'danger';
}

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
  form.username = (camera as unknown as Record<string, string>).username ?? 'admin';
  form.password = '';
  form.status = camera.status;
  dialogVisible.value = true;
}

async function handleSubmit(): Promise<void> {
  if (!form.name || !form.location || !form.ip) {
    ElMessage.error('Name, location, and IP are required.');
    return;
  }

  submitLoading.value = true;
  try {
    if (isEditing.value && editingId.value !== null) {
      const payload: Record<string, unknown> = {
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
      ElMessage.success('Camera updated.');
    } else {
      if (!form.username || !form.password) {
        ElMessage.error('Username and password are required for new cameras.');
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
      ElMessage.success('Camera created.');
    }
    dialogVisible.value = false;
    await loadCameras();
  } catch {
    ElMessage.error(isEditing.value ? 'Failed to update camera.' : 'Failed to create camera.');
  } finally {
    submitLoading.value = false;
  }
}

async function handleDelete(id: number): Promise<void> {
  deleteLoading.value = id;
  try {
    await deleteCamera(id);
    ElMessage.success('Camera deleted.');
    await loadCameras();
  } catch {
    ElMessage.error('Failed to delete camera.');
  } finally {
    deleteLoading.value = null;
  }
}

async function loadCameras(): Promise<void> {
  loading.value = true;
  try {
    cameras.value = await listCameras({ limit: 100 });
  } catch {
    ElMessage.error('Failed to load cameras.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadCameras();
});
</script>
