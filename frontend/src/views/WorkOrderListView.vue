<template>
  <section class="page-card">
    <h2 class="page-title">Work Orders</h2>
    <p class="page-subtitle">Work-order list loaded from GET /api/work-orders.</p>

    <div class="filter-bar">
      <el-select v-model="statusFilter" placeholder="Status" clearable style="width: 200px" @change="currentPage = 1">
        <el-option label="All" value="" />
        <el-option label="Open" value="open" />
        <el-option label="In Progress" value="in_progress" />
        <el-option label="Closed" value="closed" />
        <el-option label="Cancelled" value="cancelled" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="pagedWorkOrders" row-key="id" stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column prop="alert_id" label="Alert ID" width="120" />
      <el-table-column prop="status" label="Status" width="160">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Assigned To" width="160">
        <template #default="{ row }">
          <template v-if="row.assigned_to != null">
            {{ userName(row.assigned_to) }}
          </template>
          <el-tag v-else type="warning" disable-transitions>Unassigned</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="notes" label="Notes" min-width="220" show-overflow-tooltip />
      <el-table-column label="Actions" width="280" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'open'">
            <el-button type="primary" size="small" :loading="acting === row.id" @click="handleStart(row.id)">
              Start
            </el-button>
            <el-button type="success" size="small" :loading="acting === row.id" @click="handleAssign(row.id)">
              Assign
            </el-button>
          </template>
          <template v-else-if="row.status === 'in_progress'">
            <el-button type="success" size="small" :loading="acting === row.id" @click="handleClose(row.id)">
              Close
            </el-button>
            <el-button type="danger" size="small" :loading="acting === row.id" @click="handleCancel(row.id)">
              Cancel
            </el-button>
          </template>
          <template v-else>
            <el-tag type="info" disable-transitions>Done</el-tag>
          </template>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">No work orders found.</span>
      </template>
    </el-table>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredWorkOrders.length"
        layout="total, sizes, prev, pager, next"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, ref } from 'vue';

import {
  listWorkOrders,
  transitionWorkOrder,
  assignWorkOrder,
  listUsers,
} from '@/api/resources';
import type { User, WorkOrder } from '@/api/types';
import { workOrderStatusTagType } from '@/utils/tagType';
import { DEFAULT_LIST_LIMIT, USER_SELECT_LIMIT } from '@/utils/constants';

const workOrders = ref<WorkOrder[]>([]);
const users = ref<User[]>([]);
const loading = ref(false);
const acting = ref<number | null>(null);
const currentPage = ref(1);
const pageSize = ref(10);
const statusFilter = ref('');

const userMap = computed(() => {
  const map = new Map<number, User>();
  for (const u of users.value) {
    map.set(u.id, u);
  }
  return map;
});

function userName(id: number): string {
  return userMap.value.get(id)?.display_name ?? `User #${id}`;
}

const filteredWorkOrders = computed(() => {
  if (!statusFilter.value) return workOrders.value;
  return workOrders.value.filter((w) => w.status === statusFilter.value);
});

const pagedWorkOrders = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredWorkOrders.value.slice(start, start + pageSize.value);
});

const statusType = workOrderStatusTagType;

async function loadWorkOrders(): Promise<void> {
  loading.value = true;
  try {
    workOrders.value = await listWorkOrders({ limit: DEFAULT_LIST_LIMIT });
  } catch {
    ElMessage.error('Failed to load work orders.');
  } finally {
    loading.value = false;
  }
}

async function loadUsers(): Promise<void> {
  try {
    users.value = await listUsers({ limit: USER_SELECT_LIMIT });
  } catch {
    // Silently fail — names will fall back to ID display
  }
}

async function handleStart(id: number): Promise<void> {
  acting.value = id;
  try {
    await transitionWorkOrder(id, { target: 'in_progress' });
    ElMessage.success('Work order started.');
    await loadWorkOrders();
  } catch {
    ElMessage.error('Failed to start work order.');
  } finally {
    acting.value = null;
  }
}

async function handleClose(id: number): Promise<void> {
  try {
    const { value: notes } = await ElMessageBox.prompt('Optional closing notes', 'Close Work Order', {
      confirmButtonText: 'Close',
      cancelButtonText: 'Cancel',
      inputPlaceholder: 'Notes (optional)',
    });
    acting.value = id;
    await transitionWorkOrder(id, { target: 'closed', notes: notes || undefined });
    ElMessage.success('Work order closed.');
    await loadWorkOrders();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error('Failed to close work order.');
    }
  } finally {
    acting.value = null;
  }
}

async function handleCancel(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm('Are you sure you want to cancel this work order?', 'Cancel Work Order', {
      confirmButtonText: 'Cancel Order',
      cancelButtonText: 'Keep',
      type: 'warning',
    });
    acting.value = id;
    await transitionWorkOrder(id, { target: 'cancelled' });
    ElMessage.success('Work order cancelled.');
    await loadWorkOrders();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error('Failed to cancel work order.');
    }
  } finally {
    acting.value = null;
  }
}

async function handleAssign(id: number): Promise<void> {
  try {
    const { value: rawUserId } = await ElMessageBox.prompt('Enter user ID to assign', 'Assign Work Order', {
      confirmButtonText: 'Assign',
      cancelButtonText: 'Cancel',
      inputPlaceholder: 'User ID (number)',
      inputPattern: /^\d+$/,
      inputErrorMessage: 'Please enter a valid numeric user ID',
    });
    acting.value = id;
    await assignWorkOrder(id, { user_id: Number(rawUserId) });
    ElMessage.success('Work order assigned.');
    await loadWorkOrders();
  } catch (err: unknown) {
    if (err !== 'cancel' && err instanceof Error && err.message !== 'cancel') {
      ElMessage.error('Failed to assign work order.');
    }
  } finally {
    acting.value = null;
  }
}

onMounted(() => {
  void loadWorkOrders();
  void loadUsers();
});
</script>
