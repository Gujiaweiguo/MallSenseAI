import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

import { useAuthStore } from '@/auth/store';

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean;
    adminOnly?: boolean;
    title?: string;
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: 'auth.login' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: 'nav.dashboard' },
      },
      {
        path: 'cameras',
        name: 'cameras',
        component: () => import('@/views/CameraListView.vue'),
        meta: { title: 'nav.cameras' },
      },
      {
        path: 'cameras/:id',
        name: 'camera-detail',
        component: () => import('@/views/CameraDetailView.vue'),
        meta: { title: 'camera.detailTitle' },
      },
      {
        path: 'cameras/:id/rules',
        name: 'camera-rules',
        component: () => import('@/views/RuleConfigView.vue'),
        meta: { title: 'rule.title' },
      },
      {
        path: 'scenes',
        name: 'scenes',
        component: () => import('@/views/SceneListView.vue'),
        meta: { title: 'nav.scenes' },
      },
      {
        path: 'scenes/:id',
        name: 'scene-detail',
        component: () => import('@/views/SceneDetailView.vue'),
        meta: { title: 'scene.detailTitle' },
      },
      {
        path: 'alerts',
        name: 'alerts',
        component: () => import('@/views/AlertListView.vue'),
        meta: { title: 'nav.alerts' },
      },
      {
        path: 'detection-events',
        name: 'detection-events',
        component: () => import('@/views/DetectionEventListView.vue'),
        meta: { title: 'nav.detectionEvents' },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: () => import('@/views/WorkOrderListView.vue'),
        meta: { title: 'nav.workOrders' },
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('@/views/NotificationConfigView.vue'),
        meta: { title: 'nav.notifications' },
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/UserListView.vue'),
        meta: { title: 'nav.users', adminOnly: true },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  auth.initializeFromStorage();

  if (to.name === 'login' && auth.isAuthenticated) {
    return { path: '/' };
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    };
  }

  if (to.meta.adminOnly && !auth.isAdmin) {
    return { path: '/' };
  }

  return true;
});

export default router;
