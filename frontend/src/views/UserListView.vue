<template>
  <section class="page-card">
    <h2 class="page-title">Users</h2>
    <p class="page-subtitle">Admin-only user list loaded from GET /api/users.</p>

    <el-table v-loading="loading" :data="pagedUsers" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="username" label="Username" min-width="170" />
      <el-table-column prop="display_name" label="Display Name" min-width="180" />
      <el-table-column prop="role" label="Role" width="130" />
      <el-table-column label="Enabled" width="120">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Yes' : 'No' }}</el-tag>
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
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import { listUsers } from '@/api/resources';
import type { User } from '@/api/types';

const users = ref<User[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);

const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return users.value.slice(start, start + pageSize.value);
});

async function loadUsers(): Promise<void> {
  loading.value = true;
  try {
    users.value = await listUsers({ limit: 100 });
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
