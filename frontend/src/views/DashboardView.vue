<template>
  <section class="dashboard-view">
    <div class="dashboard-view__grid">
      <el-card v-for="stat in stats" :key="stat.label" class="dashboard-view__card" shadow="never">
        <p>{{ stat.label }}</p>
        <strong>{{ stat.value }}</strong>
        <span>{{ stat.hint }}</span>
      </el-card>
    </div>
  </section>
</template>

<script setup lang="ts">
interface DashboardStat {
  label: string;
  value: string;
  hint: string;
}

const stats: DashboardStat[] = [
  { label: 'Total Cameras', value: '0', hint: 'Placeholder until metrics API is connected' },
  { label: 'Active Alerts', value: '0', hint: 'Live alert summary coming later' },
  { label: 'Open Work Orders', value: '0', hint: 'Workflow counts will use real API data' },
];
</script>

<style scoped>
.dashboard-view__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--ms-space-5);
}

.dashboard-view__card {
  border: 1px solid var(--ms-color-border);
  border-radius: var(--ms-radius-2);
  box-shadow: var(--ms-shadow-card);
}

.dashboard-view__card p {
  margin: 0 0 var(--ms-space-3);
  color: var(--ms-color-muted);
}

.dashboard-view__card strong {
  display: block;
  margin-bottom: var(--ms-space-2);
  font-size: 36px;
  color: var(--ms-color-header-text);
}

.dashboard-view__card span {
  color: var(--ms-color-muted);
  font-size: 13px;
}
</style>
