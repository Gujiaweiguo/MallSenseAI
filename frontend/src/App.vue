<template>
  <el-config-provider :locale="elementLocale">
    <RouterView />
  </el-config-provider>
</template>

<script setup lang="ts">
import en from 'element-plus/es/locale/lang/en';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import { computed } from 'vue';

import i18n from '@/i18n';

const localeMap = { 'zh-CN': zhCn, en } as const;
const elementLocale = computed(() => localeMap[i18n.global.locale.value as keyof typeof localeMap] ?? zhCn);
</script>
