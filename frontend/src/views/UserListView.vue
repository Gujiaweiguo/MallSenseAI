<template>
  <section class="page-card">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('user.title') }}</h2>
        <p class="page-subtitle">{{ t('user.subtitle') }}</p>
      </div>
      <el-button v-if="auth.isAdmin" type="primary" @click="openCreateDialog">
        {{ t('common.button.addUser') }}
      </el-button>
    </div>

    <el-table v-loading="loading" :data="pagedUsers" row-key="id" stripe>
      <el-table-column prop="id" :label="t('common.table.id')" width="70" />
      <el-table-column prop="username" :label="t('common.table.username')" min-width="150" />
      <el-table-column prop="display_name" :label="t('common.table.displayName')" min-width="160" />
      <el-table-column :label="t('common.table.role')" width="120">
        <template #default="{ row }">
          {{ t('common.enum.userRole.' + row.role) }}
        </template>
      </el-table-column>
      <el-table-column :label="t('common.table.enabled')" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">
            {{ t('common.enum.enabledDisabled.' + (row.enabled ? 'enabled' : 'disabled')) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.table.actions')" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">{{ t('common.button.edit') }}</el-button>
          <el-button size="small" @click="toggleEnabled(row)">
            {{ row.enabled ? t('common.button.disable') : t('common.button.enable') }}
          </el-button>
          <el-popconfirm
            v-if="auth.isAdmin"
            :title="t('user.deleteConfirm')"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger">{{ t('common.button.delete') }}</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noUsers') }}</span>
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

    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? t('user.editUser') : t('user.addUser')"
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
        <el-form-item :label="t('user.formUsername')" prop="username">
          <el-input v-model="form.username" autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('user.formDisplayName')" prop="display_name">
          <el-input v-model="form.display_name" autocomplete="off" />
        </el-form-item>
        <el-form-item :label="t('user.formPassword')" :prop="isEditing ? '' : 'password'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEditing ? t('user.phPasswordKeep') : undefined"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item :label="t('user.formRole')" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option :label="t('common.enum.userRole.admin')" value="admin" />
            <el-option :label="t('common.enum.userRole.operator')" value="operator" />
            <el-option :label="t('common.enum.userRole.viewer')" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('user.formEnabled')">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.button.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEditing ? t('common.button.save') : t('common.button.create') }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { createUser, deleteUser, listUsers, updateUser } from '@/api/resources';
import type { User, UserCreatePayload, UserUpdatePayload, UserRole } from '@/api/types';
import { useAuthStore } from '@/auth/store';
import { DEFAULT_LIST_LIMIT } from '@/utils/constants';

const { t } = useI18n();
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
  username: [{ required: true, message: t('user.validation.usernameRequired'), trigger: 'blur' }],
  display_name: [{ required: true, message: t('user.validation.displayNameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: t('user.validation.passwordRequired'), trigger: 'blur' }],
  role: [{ required: true, message: t('user.validation.roleRequired'), trigger: 'change' }],
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
      ElMessage.success(t('user.toastUpdated'));
    } else {
      const payload: UserCreatePayload = {
        username: form.username,
        display_name: form.display_name,
        password: form.password,
        role: form.role,
        enabled: form.enabled,
      };
      await createUser(payload);
      ElMessage.success(t('user.toastCreated'));
    }
    dialogVisible.value = false;
    await loadUsers();
  } catch {
    ElMessage.error(isEditing.value ? t('user.toastUpdateFailed') : t('user.toastCreateFailed'));
  } finally {
    submitting.value = false;
  }
}

async function toggleEnabled(user: User): Promise<void> {
  try {
    await updateUser(user.id, { enabled: !user.enabled });
    ElMessage.success(user.enabled ? t('user.toastDisabled') : t('user.toastEnabled'));
    await loadUsers();
  } catch {
    ElMessage.error(t('user.toastToggleFailed'));
  }
}

async function handleDelete(id: number): Promise<void> {
  try {
    await deleteUser(id);
    ElMessage.success(t('user.toastDeleted'));
    await loadUsers();
  } catch {
    ElMessage.error(t('user.toastDeleteFailed'));
  }
}

async function loadUsers(): Promise<void> {
  loading.value = true;
  try {
    users.value = await listUsers({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error(t('user.toastLoadFailed'));
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
