<template>
  <el-container class="main-layout">
    <el-aside class="main-layout__aside" width="var(--ms-sidebar-width)">
      <div class="main-layout__brand">
        <span class="main-layout__brand-mark">MS</span>
        <span>MallSenseAI</span>
      </div>
      <el-menu
        class="main-layout__menu"
        :default-active="activeMenu"
        router
        background-color="var(--ms-color-sidebar)"
        text-color="var(--ms-color-sidebar-text)"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/cameras">
          <el-icon><VideoCamera /></el-icon>
          <span>Cameras</span>
        </el-menu-item>
        <el-menu-item index="/scenes">
          <el-icon><Picture /></el-icon>
          <span>Scenes</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>Alerts</span>
        </el-menu-item>
        <el-menu-item index="/work-orders">
          <el-icon><Tickets /></el-icon>
          <span>Work Orders</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>Users</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="main-layout__header">
        <div>
          <h1 class="main-layout__title">{{ route.meta.title ?? 'Console' }}</h1>
        </div>
        <div class="main-layout__account">
          <span class="main-layout__user">{{ auth.user?.display_name ?? auth.user?.username }}</span>
          <el-tag size="small" type="info">{{ auth.user?.role ?? 'viewer' }}</el-tag>
          <el-button type="primary" plain @click="handleLogout">Logout</el-button>
        </div>
      </el-header>

      <el-main class="main-layout__content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { DataBoard, Picture, Tickets, User, VideoCamera, Warning } from '@element-plus/icons-vue';
import { computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { useAuthStore } from '@/auth/store';
import { useAlertEvents } from '@/composables/useAlertEvents';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const alertWs = useAlertEvents();

const activeMenu = computed(() => {
  if (route.path.startsWith('/cameras')) {
    return '/cameras';
  }
  return route.path;
});

function handleLogout(): void {
  alertWs.disconnect();
  auth.logout();
  void router.replace('/login');
}

onMounted(() => {
  if (auth.isAuthenticated) {
    alertWs.connect();
  }
});

onUnmounted(() => {
  alertWs.disconnect();
});
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  background: var(--ms-color-page);
}

.main-layout__aside {
  min-height: 100vh;
  background: var(--ms-color-sidebar);
}

.main-layout__brand {
  display: flex;
  align-items: center;
  gap: var(--ms-space-3);
  height: 64px;
  padding: 0 var(--ms-space-5);
  color: #ffffff;
  font-size: 18px;
  font-weight: 700;
  border-bottom: 1px solid rgb(255 255 255 / 12%);
}

.main-layout__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--ms-radius-1);
  background: #2563eb;
  font-size: 13px;
  letter-spacing: 0.04em;
}

.main-layout__menu {
  border-right: 0;
}

.main-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 var(--ms-space-5);
  background: var(--ms-color-surface);
  border-bottom: 1px solid var(--ms-color-border);
}

.main-layout__title {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
  color: var(--ms-color-header-text);
}

.main-layout__account {
  display: flex;
  align-items: center;
  gap: var(--ms-space-3);
}

.main-layout__user {
  color: var(--ms-color-header-text);
  font-weight: 600;
}

.main-layout__content {
  padding: var(--ms-space-5);
}
</style>
