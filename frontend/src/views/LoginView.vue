<template>
  <main class="login-view">
    <section class="login-view__panel">
      <div class="login-view__intro">
        <p class="login-view__eyebrow">{{ t('auth.consoleTitle') }}</p>
        <h1>{{ t('auth.intro') }}</h1>
        <p>{{ t('auth.hint') }}</p>
      </div>

      <el-card class="login-view__card" shadow="never">
        <template #header>
          <div class="login-view__card-header">{{ t('auth.login') }}</div>
        </template>

        <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
          <el-form-item :label="t('auth.username')" required>
            <el-input v-model="form.username" autocomplete="username" :placeholder="t('auth.usernamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('auth.password')" required>
            <el-input
              v-model="form.password"
              autocomplete="current-password"
              :placeholder="t('auth.passwordPlaceholder')"
              show-password
              type="password"
            />
          </el-form-item>
          <el-button class="login-view__submit" type="primary" native-type="submit" :loading="loading">
            {{ t('common.button.signIn') }}
          </el-button>
        </el-form>
      </el-card>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus';
import { computed, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { useAuthStore } from '@/auth/store';

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const form = reactive({
  username: '',
  password: '',
});
const loading = ref(false);

const redirectPath = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/'));

async function handleSubmit(): Promise<void> {
  if (form.username.trim().length === 0 || form.password.length === 0) {
    ElMessage.warning(t('auth.required'));
    return;
  }

  loading.value = true;
  try {
    await auth.login({ username: form.username.trim(), password: form.password });
    ElMessage.success(t('auth.success'));
    await router.replace(redirectPath.value);
  } catch {
    ElMessage.error(t('auth.failed'));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--ms-space-6);
  background:
    radial-gradient(circle at top left, rgb(37 99 235 / 18%), transparent 34%),
    linear-gradient(135deg, #eef4ff 0%, #f8fbff 50%, #f4f7fb 100%);
}

.login-view__panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: var(--ms-space-6);
  width: min(980px, 100%);
  align-items: center;
}

.login-view__intro h1 {
  margin: 0 0 var(--ms-space-4);
  color: var(--ms-color-header-text);
  font-size: 42px;
  line-height: 1.1;
}

.login-view__intro p {
  color: var(--ms-color-muted);
  font-size: 16px;
}

.login-view__eyebrow {
  margin: 0 0 var(--ms-space-3);
  color: #2563eb !important;
  font-size: 13px !important;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.login-view__card {
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-2);
  box-shadow: var(--ms-shadow-card);
}

.login-view__card-header {
  font-size: 18px;
  font-weight: 650;
}

.login-view__submit {
  width: 100%;
}
</style>
