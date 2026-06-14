<template>
  <div class="camera-scenes-redirect">
    <el-icon class="is-loading" :size="24"><Loading /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue';
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { listScenes } from '@/api/resources';

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  const cameraId = Number(route.params.id);
  try {
    const scenes = await listScenes(cameraId);
    if (scenes.length > 0) {
      void router.replace(`/scenes/${scenes[0].id}`);
    } else {
      void router.replace(`/cameras/${cameraId}`);
    }
  } catch {
    void router.replace(`/cameras/${cameraId}`);
  }
});
</script>

<style scoped>
.camera-scenes-redirect {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--el-text-color-secondary);
}
</style>
