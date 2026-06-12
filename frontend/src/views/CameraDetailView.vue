<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">Camera Detail</h2>
        <p class="page-subtitle">View and edit camera details.</p>
      </div>
      <div v-if="camera" class="detail-actions">
        <el-button v-if="!editing" type="primary" @click="startEditing">Edit</el-button>
        <template v-else>
          <el-button @click="cancelEditing">Cancel</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">Save</el-button>
        </template>
        <el-popconfirm
          title="Delete this camera?"
          confirm-button-text="Delete"
          cancel-button-text="Cancel"
          confirm-button-type="danger"
          @confirm="handleDelete"
        >
          <template #reference>
            <el-button type="danger" :loading="deleting">Delete</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="5" animated />

    <!-- Read mode -->
    <el-descriptions v-else-if="camera && !editing" :column="2" border>
      <el-descriptions-item label="ID">{{ camera.id }}</el-descriptions-item>
      <el-descriptions-item label="Name">{{ camera.name }}</el-descriptions-item>
      <el-descriptions-item label="Location">{{ camera.location }}</el-descriptions-item>
      <el-descriptions-item label="IP">{{ camera.ip }}</el-descriptions-item>
      <el-descriptions-item label="Port">{{ camera.port }}</el-descriptions-item>
      <el-descriptions-item label="Status">
        <el-tag :type="statusType(camera.status)">{{ camera.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="Created">{{ camera.created_at }}</el-descriptions-item>
      <el-descriptions-item label="Updated">{{ camera.updated_at }}</el-descriptions-item>
    </el-descriptions>

    <!-- Edit mode -->
    <el-form v-else-if="camera && editing" :model="editForm" label-width="100px" style="max-width: 600px">
      <el-form-item label="Name" required>
        <el-input v-model="editForm.name" />
      </el-form-item>
      <el-form-item label="Location" required>
        <el-input v-model="editForm.location" />
      </el-form-item>
      <el-form-item label="IP" required>
        <el-input v-model="editForm.ip" />
      </el-form-item>
      <el-form-item label="Port">
        <el-input-number v-model="editForm.port" :min="1" :max="65535" />
      </el-form-item>
      <el-form-item label="Status">
        <el-select v-model="editForm.status">
          <el-option label="Active" value="active" />
          <el-option label="Inactive" value="inactive" />
          <el-option label="Maintenance" value="maintenance" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-empty v-else description="Camera not found" />

    <!-- Related links -->
    <div v-if="camera" class="related-links">
      <h3>Related</h3>
      <ul>
        <li><RouterLink :to="`/scenes?camera_id=${camera.id}`">Scenes for this camera</RouterLink></li>
        <li><RouterLink :to="`/cameras/${camera.id}/rules`">Rules for this camera</RouterLink></li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { deleteCamera, getCamera, updateCamera } from '@/api/cameras';
import type { Camera, CameraStatus } from '@/api/types';

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
  port: 80,
  status: 'active',
});

function statusType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  if (status === 'active') return 'success';
  if (status === 'maintenance') return 'warning';
  if (status === 'inactive') return 'info';
  return 'danger';
}

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
    ElMessage.error('Name, location, and IP are required.');
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
    ElMessage.success('Camera updated.');
  } catch {
    ElMessage.error('Failed to update camera.');
  } finally {
    saving.value = false;
  }
}

async function handleDelete(): Promise<void> {
  if (!camera.value) return;
  deleting.value = true;
  try {
    await deleteCamera(camera.value.id);
    ElMessage.success('Camera deleted.');
    void router.push('/cameras');
  } catch {
    ElMessage.error('Failed to delete camera.');
  } finally {
    deleting.value = false;
  }
}

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
