<template>
  <section class="page-card rule-config">
    <div class="rule-config__header">
      <div>
        <h2 class="page-title">Rule Configuration</h2>
        <p class="page-subtitle">Configure ROI-based detection rules for camera #{{ cameraId }}.</p>
      </div>
      <el-button type="primary" @click="openCreateForm">Create Rule</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-table v-loading="loading" :data="rules" row-key="id" stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="rule_type" label="Type" min-width="150" />
          <el-table-column label="ROI" min-width="140">
            <template #default="{ row }">{{ roiName(row.roi_id) }}</template>
          </el-table-column>
          <el-table-column prop="priority" label="Priority" width="100" />
          <el-table-column label="Enabled" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Enabled' : 'Disabled' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Thresholds" min-width="220">
            <template #default="{ row }">{{ formatThresholds(row.threshold_config) }}</template>
          </el-table-column>
          <el-table-column label="Actions" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openEditForm(row)">Edit</el-button>
              <el-button type="danger" link @click="confirmDeleteRule(row)">Delete</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="empty-note">No rules configured.</span>
          </template>
        </el-table>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never">
          <template #header>{{ editingRuleId === null ? 'Create Rule' : `Edit Rule #${editingRuleId}` }}</template>
          <el-form label-position="top" :model="form">
            <el-form-item label="Rule Type">
              <el-select v-model="form.rule_type" class="rule-config__full">
                <el-option label="Passable Zone" value="passable_zone" />
                <el-option label="Forbidden Zone" value="forbidden_zone" />
                <el-option label="Object Count" value="object_count" />
              </el-select>
            </el-form-item>
            <el-form-item label="ROI">
              <el-select v-model="form.roi_id" class="rule-config__full" clearable placeholder="Optional ROI">
                <el-option v-for="roi in rois" :key="roi.id" :label="roi.name" :value="roi.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="Threshold">
              <el-input-number v-model="form.threshold_config.threshold" :min="0" :step="0.05" class="rule-config__full" />
            </el-form-item>
            <el-form-item label="Minimum Area">
              <el-input-number v-model="form.threshold_config.min_area" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item label="Maximum Count">
              <el-input-number v-model="form.threshold_config.max_count" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item label="Duration Seconds">
              <el-input-number v-model="form.threshold_config.duration_seconds" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item label="Priority">
              <el-input-number v-model="form.priority" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item label="Enabled">
              <el-switch v-model="form.enabled" />
            </el-form-item>
            <div class="rule-config__form-actions">
              <el-button @click="resetForm">Reset</el-button>
              <el-button type="primary" :loading="saving" @click="submitForm">
                {{ editingRuleId === null ? 'Create' : 'Save' }}
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import { createRule, deleteRule, listRois, listRules, listScenes, updateRule } from '@/api/resources';
import type { Roi, Rule, RuleCreatePayload, RuleThresholdConfig, RuleType, Scene } from '@/api/types';

interface RuleForm {
  rule_type: RuleType;
  roi_id: number | null;
  threshold_config: RuleThresholdConfig;
  priority: number;
  enabled: boolean;
}

const route = useRoute();
const cameraId = computed(() => Number(route.params.id));
const loading = ref(false);
const saving = ref(false);
const rules = ref<Rule[]>([]);
const scenes = ref<Scene[]>([]);
const rois = ref<Roi[]>([]);
const editingRuleId = ref<number | null>(null);
const form = reactive<RuleForm>(defaultForm());

function defaultForm(): RuleForm {
  return {
    rule_type: 'passable_zone',
    roi_id: null,
    threshold_config: {
      threshold: 0.8,
      min_area: 0,
      max_count: 1,
      duration_seconds: 0,
    },
    priority: 1,
    enabled: true,
  };
}

function assignForm(next: RuleForm): void {
  form.rule_type = next.rule_type;
  form.roi_id = next.roi_id;
  form.threshold_config = { ...next.threshold_config };
  form.priority = next.priority;
  form.enabled = next.enabled;
}

function resetForm(): void {
  editingRuleId.value = null;
  assignForm(defaultForm());
}

function openCreateForm(): void {
  resetForm();
}

function openEditForm(rule: Rule): void {
  editingRuleId.value = rule.id;
  assignForm({
    rule_type: rule.rule_type,
    roi_id: rule.roi_id,
    threshold_config: { ...rule.threshold_config },
    priority: rule.priority,
    enabled: rule.enabled,
  });
}

function compactThresholdConfig(config: RuleThresholdConfig): RuleThresholdConfig {
  const entries = Object.entries(config).filter((entry): entry is [keyof RuleThresholdConfig, number] => {
    const value = entry[1];
    return typeof value === 'number' && Number.isFinite(value);
  });
  return Object.fromEntries(entries) as RuleThresholdConfig;
}

function payloadFromForm(): RuleCreatePayload {
  return {
    camera_id: cameraId.value,
    rule_type: form.rule_type,
    roi_id: form.roi_id,
    threshold_config: compactThresholdConfig(form.threshold_config),
    priority: form.priority,
    enabled: form.enabled,
  };
}

function roiName(roiId: number | null): string {
  if (roiId === null) {
    return 'All scene';
  }
  return rois.value.find((roi) => roi.id === roiId)?.name ?? `ROI #${roiId}`;
}

function formatThresholds(config: RuleThresholdConfig): string {
  const pairs = Object.entries(config).filter(([, value]) => value !== undefined);
  return pairs.length === 0 ? 'None' : pairs.map(([key, value]) => `${key}: ${value}`).join(', ');
}

async function loadData(): Promise<void> {
  if (!Number.isInteger(cameraId.value)) {
    ElMessage.error('Invalid camera ID.');
    return;
  }
  loading.value = true;
  try {
    const [ruleData, sceneData] = await Promise.all([listRules(cameraId.value), listScenes(cameraId.value)]);
    rules.value = ruleData;
    scenes.value = sceneData;
    const roiGroups = await Promise.all(sceneData.map((scene) => listRois(scene.id)));
    rois.value = roiGroups.flat();
  } catch {
    ElMessage.error('Failed to load rules.');
  } finally {
    loading.value = false;
  }
}

async function submitForm(): Promise<void> {
  saving.value = true;
  try {
    if (editingRuleId.value === null) {
      const created = await createRule(payloadFromForm());
      rules.value.push(created);
      ElMessage.success('Rule created.');
    } else {
      const { camera_id: _cameraId, ...updatePayload } = payloadFromForm();
      const updated = await updateRule(editingRuleId.value, updatePayload);
      rules.value = rules.value.map((rule) => (rule.id === updated.id ? updated : rule));
      ElMessage.success('Rule updated.');
    }
    resetForm();
  } catch {
    ElMessage.error('Failed to save rule.');
  } finally {
    saving.value = false;
  }
}

async function confirmDeleteRule(rule: Rule): Promise<void> {
  try {
    await ElMessageBox.confirm(`Delete rule #${rule.id}?`, 'Delete Rule', { type: 'warning' });
    await deleteRule(rule.id);
    rules.value = rules.value.filter((item) => item.id !== rule.id);
    ElMessage.success('Rule deleted.');
    if (editingRuleId.value === rule.id) {
      resetForm();
    }
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error('Failed to delete rule.');
  }
}

onMounted(() => {
  void loadData();
});
</script>

<style scoped>
.rule-config__header,
.rule-config__form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rule-config__full {
  width: 100%;
}

.rule-config__form-actions {
  justify-content: flex-end;
}
</style>
