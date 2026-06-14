<template>
  <el-container class="main-layout">
    <el-aside class="main-layout__aside" width="var(--ms-sidebar-width)">
      <div class="main-layout__brand">
        <span class="main-layout__brand-mark">MS</span>
        <span>{{ t('common.brand') }}</span>
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
          <span>{{ t('nav.dashboard') }}</span>
        </el-menu-item>
        <el-menu-item index="/cameras">
          <el-icon><VideoCamera /></el-icon>
          <span>{{ t('nav.cameras') }}</span>
        </el-menu-item>
        <el-menu-item index="/scenes">
          <el-icon><Picture /></el-icon>
          <span>{{ t('nav.scenes') }}</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>{{ t('nav.alerts') }}</span>
        </el-menu-item>
        <el-menu-item index="/detection-events">
          <el-icon><Monitor /></el-icon>
          <span>{{ t('nav.detectionEvents') }}</span>
        </el-menu-item>
        <el-menu-item index="/work-orders">
          <el-icon><Tickets /></el-icon>
          <span>{{ t('nav.workOrders') }}</span>
        </el-menu-item>
        <el-menu-item index="/rule-definitions">
          <el-icon><Setting /></el-icon>
          <span>{{ t('nav.ruleDefinitions') }}</span>
        </el-menu-item>
        <el-menu-item index="/notifications">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ t('nav.notifications') }}</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>{{ t('nav.users') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="main-layout__header">
        <div>
          <h1 class="main-layout__title">{{ pageTitle }}</h1>
        </div>
        <div class="main-layout__account">
          <LocaleSwitcher />
          <span class="main-layout__user">{{ auth.user?.display_name ?? auth.user?.username }}</span>
          <el-tag size="small" type="info">{{ t('common.enum.userRole.' + (auth.user?.role ?? 'viewer')) }}</el-tag>
          <el-badge :value="unreadAlertCount" :hidden="unreadAlertCount === 0">
            <el-button class="main-layout__notification-button" text @click="handleAlertNavigation">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-button type="primary" plain @click="handleLogout">{{ t('common.button.logout') }}</el-button>
        </div>
      </el-header>

      <el-main class="main-layout__content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { Bell, ChatDotRound, DataBoard, Monitor, Picture, Setting, Tickets, User, VideoCamera, Warning } from '@element-plus/icons-vue';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import LocaleSwitcher from '@/components/LocaleSwitcher.vue';
import { useAuthStore } from '@/auth/store';
import { useAlertEvents } from '@/composables/useAlertEvents';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const alertWs = useAlertEvents();
const unreadAlertCount = ref(0);

const pageTitle = computed(() => {
  const titleKey = route.meta.title as string | undefined;
  return titleKey ? t(titleKey) : t('common.brand');
});

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

function playNotificationSound(): void {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 800;
    gain.gain.value = 0.3;
    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch {
    // ignore if audio not available
  }
}

function handleAlertNavigation(): void {
  unreadAlertCount.value = 0;
  void router.push('/alerts');
}

watch(
  () => alertWs.lastEvent.value,
  (event) => {
    if (!event || event.event_type !== 'created') return;
    unreadAlertCount.value += 1;
    playNotificationSound();
  },
);

watch(
  () => route.path,
  (path) => {
    if (path === '/alerts') {
      unreadAlertCount.value = 0;
    }
  },
  { immediate: true },
);

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

.main-layout__notification-button {
  padding: 6px;
  color: var(--ms-color-header-text);
}

.main-layout__content {
  padding: var(--ms-space-5);
}
</style>
