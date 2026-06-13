<template>
  <el-dropdown @command="handleChange">
    <span class="locale-switcher">
      {{ currentLabel }}
      <el-icon><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item v-for="l in locales" :key="l.value" :command="l.value">
          {{ l.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { ArrowDown } from '@element-plus/icons-vue';
import { computed } from 'vue';

import i18n, { setLocale, type AppLocale } from '@/i18n';

const locales: { value: AppLocale; label: string }[] = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en', label: 'English' },
];

const currentLabel = computed(() => (i18n.global.locale.value === 'zh-CN' ? '中文' : 'English'));

function handleChange(val: AppLocale): void {
  setLocale(val);
}
</script>

<style scoped>
.locale-switcher {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--ms-color-header-text);
  font-size: 14px;
}
</style>
