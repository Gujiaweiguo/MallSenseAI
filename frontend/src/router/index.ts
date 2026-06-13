import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

import { useAuthStore } from '@/auth/store';
import AlertListView from '@/views/AlertListView.vue';
import CameraDetailView from '@/views/CameraDetailView.vue';
import CameraListView from '@/views/CameraListView.vue';
import DashboardView from '@/views/DashboardView.vue';
import DetectionEventListView from '@/views/DetectionEventListView.vue';
import LoginView from '@/views/LoginView.vue';
import RuleConfigView from '@/views/RuleConfigView.vue';
import SceneDetailView from '@/views/SceneDetailView.vue';
import SceneListView from '@/views/SceneListView.vue';
import UserListView from '@/views/UserListView.vue';
import WorkOrderListView from '@/views/WorkOrderListView.vue';

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
    component: LoginView,
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
        component: DashboardView,
        meta: { title: 'Dashboard' },
      },
      {
        path: 'cameras',
        name: 'cameras',
        component: CameraListView,
        meta: { title: 'Cameras' },
      },
      {
        path: 'cameras/:id',
        name: 'camera-detail',
        component: CameraDetailView,
        meta: { title: 'Camera Detail' },
      },
      {
        path: 'cameras/:id/rules',
        name: 'camera-rules',
        component: RuleConfigView,
        meta: { title: 'Rule Configuration' },
      },
      {
        path: 'scenes',
        name: 'scenes',
        component: SceneListView,
        meta: { title: 'Scenes' },
      },
      {
        path: 'scenes/:id',
        name: 'scene-detail',
        component: SceneDetailView,
        meta: { title: 'Scene Detail' },
      },
      {
        path: 'alerts',
        name: 'alerts',
        component: AlertListView,
        meta: { title: 'Alerts' },
      },
      {
        path: 'detection-events',
        name: 'detection-events',
        component: DetectionEventListView,
        meta: { title: 'Detection Events' },
      },
      {
        path: 'work-orders',
        name: 'work-orders',
        component: WorkOrderListView,
        meta: { title: 'Work Orders' },
      },
      {
        path: 'users',
        name: 'users',
        component: UserListView,
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
