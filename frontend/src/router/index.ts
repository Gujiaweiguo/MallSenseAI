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
    meta: { title: 'Login' },
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
        meta: { title: 'Dashboard' },
      },
      {
        path: 'cameras',
        name: 'cameras',
        component: () => import('@/views/CameraListView.vue'),
        meta: { title: 'Cameras' },
      },
      {
        path: 'cameras/:id',
        name: 'camera-detail',
        component: () => import('@/views/CameraDetailView.vue'),
        meta: { title: 'Camera Detail' },
      },
      {
        path: 'cameras/:id/rules',
        name: 'camera-rules',
        component: () => import('@/views/RuleConfigView.vue'),
        meta: { title: 'Rule Configuration' },
      },
      {
        path: 'scenes',
        name: 'scenes',
        component: () => import('@/views/SceneListView.vue'),
        meta: { title: 'Scenes' },
      },
      {
        path: 'scenes/:id',
        name: 'scene-detail',
        component: () => import('@/views/SceneDetailView.vue'),
        meta: { title: 'Scene Detail' },
      },
      {
        path: 'alerts',
        name: 'alerts',
        component: () => import('@/views/AlertListView.vue'),
        meta: { title: 'Alerts' },
      },
      {
        path: 'detection-events',
        name: 'detection-events',
        component: () => import('@/views/DetectionEventListView.vue'),
        meta: { title: 'Detection Events' },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: () => import('@/views/WorkOrderListView.vue'),
        meta: { title: 'Work Orders' },
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('@/views/NotificationConfigView.vue'),
        meta: { title: 'Notifications' },
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/UserListView.vue'),
        meta: { title: 'Users', adminOnly: true },
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
