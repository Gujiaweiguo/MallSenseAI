<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">Users</h2>
        <p class="page-subtitle">Admin-only user management.</p>
      </div>
      <el-button v-if="auth.isAdmin" type="primary" @click="openCreateDialog">
        Add User
      </el-button>
    </div>

    <el-table v-loading="loading" :data="pagedUsers" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="Username" min-width="150" />
      <el-table-column prop="display_name" label="Display Name" min-width="160" />
      <el-table-column prop="role" label="Role" width="120" />
      <el-table-column label="Enabled" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? 'Yes' : 'No' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">Edit</el-button>
          <el-button size="small" @click="toggleEnabled(row)">
            {{ row.enabled ? 'Disable' : 'Enable' }}
          </el-button>
          <el-popconfirm
            v-if="auth.isAdmin"
            title="Are you sure you want to delete this user?"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger">Delete</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No users found.</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="users.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? 'Edit User' : 'Add User'"
      width="480px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="120px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Display Name" prop="display_name">
          <el-input v-model="form.display_name" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Password" :prop="isEditing ? '' : 'password'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEditing ? 'Leave blank to keep current' : undefined"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="Admin" value="admin" />
            <el-option label="Operator" value="operator" />
            <el-option label="Viewer" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="Enabled">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEditing ? 'Save' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';

import { createUser, deleteUser, listUsers, updateUser } from '@/api/resources';
import type { User, UserCreatePayload, UserUpdatePayload, UserRole } from '@/api/types';
import { useAuthStore } from '@/auth/store';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

const auth = useAuthStore();

const users = ref<User[]>([]);
const loading = ref(false);
const submitting = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

// Dialog state
const dialogVisible = ref(false);
const isEditing = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<FormInstance>();

const form = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'viewer' as UserRole,
  enabled: true,
});

const formRules: FormRules = {
  username: [{ required: true, message: 'Username is required', trigger: 'blur' }],
  display_name: [{ required: true, message: 'Display name is required', trigger: 'blur' }],
  password: [{ required: true, message: 'Password is required', trigger: 'blur' }],
  role: [{ required: true, message: 'Role is required', trigger: 'change' }],
};

const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return users.value.slice(start, start + pageSize.value);
});

function resetForm(): void {
  form.username = '';
  form.display_name = '';
  form.password = '';
  form.role = 'viewer';
  form.enabled = true;
}

function openCreateDialog(): void {
  isEditing.value = false;
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(user: User): void {
  isEditing.value = true;
  editingId.value = user.id;
  form.username = user.username;
  form.display_name = user.display_name;
  form.password = '';
  form.role = user.role;
  form.enabled = user.enabled;
  dialogVisible.value = true;
}

async function handleSubmit(): Promise<void> {
  const formEl = formRef.value;
  if (formEl === undefined) return;

  const valid = await formEl.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    if (isEditing.value && editingId.value !== null) {
      const payload: UserUpdatePayload = {
        username: form.username,
        display_name: form.display_name,
        role: form.role,
        enabled: form.enabled,
      };
      if (form.password.length > 0) {
        payload.password = form.password;
      }
      await updateUser(editingId.value, payload);
      ElMessage.success('User updated successfully.');
    } else {
      const payload: UserCreatePayload = {
        username: form.username,
        display_name: form.display_name,
        password: form.password,
        role: form.role,
        enabled: form.enabled,
      };
      await createUser(payload);
      ElMessage.success('User created successfully.');
    }
    dialogVisible.value = false;
    await loadUsers();
  } catch {
    ElMessage.error(isEditing.value ? 'Failed to update user.' : 'Failed to create user.');
  } finally {
    submitting.value = false;
  }
}

async function toggleEnabled(user: User): Promise<void> {
  try {
    await updateUser(user.id, { enabled: !user.enabled });
    ElMessage.success(`User ${user.enabled ? 'disabled' : 'enabled'} successfully.`);
    await loadUsers();
  } catch {
    ElMessage.error('Failed to toggle user status.');
  }
}

async function handleDelete(id: number): Promise<void> {
  try {
    await deleteUser(id);
    ElMessage.success('User deleted successfully.');
    await loadUsers();
  } catch {
    ElMessage.error('Failed to delete user.');
  }
}

async function loadUsers(): Promise<void> {
  loading.value = true;
  try {
    users.value = await listUsers({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error('Failed to load users.');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadUsers();
});
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
</style>
