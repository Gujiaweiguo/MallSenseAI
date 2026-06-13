<template>
  <section class="page-card rule-config">
    <div class="rule-config__header">
      <div>
        <h2 class="page-title">{{ t('rule.title') }}</h2>
        <p class="page-subtitle">{{ t('rule.subtitle', { id: cameraId }) }}</p>
      </div>
      <el-button type="primary" @click="openCreateForm">{{ t('common.button.createRule') }}</el-button>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-table v-loading="loading" :data="rules" row-key="id" stripe>
          <el-table-column prop="id" :label="t('common.table.id')" width="80" />
          <el-table-column :label="t('common.table.type')" min-width="150">
            <template #default="{ row }">{{ t('common.enum.ruleType.' + row.rule_type) }}</template>
          </el-table-column>
          <el-table-column :label="t('common.table.roi')" min-width="140">
            <template #default="{ row }">{{ roiName(row.roi_id) }}</template>
          </el-table-column>
          <el-table-column prop="priority" :label="t('common.table.priority')" width="100" />
          <el-table-column :label="t('common.table.enabled')" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ t('common.enum.enabledDisabled.' + (row.enabled ? 'enabled' : 'disabled')) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('common.table.thresholds')" min-width="220">
            <template #default="{ row }">{{ formatThresholds(row.threshold_config) }}</template>
          </el-table-column>
          <el-table-column :label="t('common.table.actions')" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openEditForm(row)">{{ t('common.button.edit') }}</el-button>
              <el-button type="danger" link @click="confirmDeleteRule(row)">{{ t('common.button.delete') }}</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="empty-note">{{ t('common.empty.noRules') }}</span>
          </template>
        </el-table>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never">
          <template #header>{{ editingRuleId === null ? t('rule.createRuleTitle') : t('rule.editRuleTitle', { id: editingRuleId }) }}</template>
          <el-form label-position="top" :model="form">
            <el-form-item :label="t('rule.formRuleType')">
              <el-select v-model="form.rule_type" class="rule-config__full">
        <el-option :label="t('common.enum.ruleType.obstruction_duration')" value="obstruction_duration" />
        <el-option :label="t('common.enum.ruleType.obstruction_area')" value="obstruction_area" />
        <el-option :label="t('common.enum.ruleType.litter')" value="litter" />
        <el-option :label="t('common.enum.ruleType.fire_smoke')" value="fire_smoke" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('rule.formRoi')">
              <el-select v-model="form.roi_id" class="rule-config__full" clearable :placeholder="t('rule.phRoi')">
                <el-option v-for="roi in rois" :key="roi.id" :label="roi.name" :value="roi.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('rule.formThreshold')">
              <el-input-number v-model="form.threshold_config.threshold" :min="0" :step="0.05" class="rule-config__full" />
            </el-form-item>
            <el-form-item :label="t('rule.formMinArea')">
              <el-input-number v-model="form.threshold_config.min_area" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item :label="t('rule.formMaxCount')">
              <el-input-number v-model="form.threshold_config.max_count" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item :label="t('rule.formDurationSeconds')">
              <el-input-number v-model="form.threshold_config.duration_seconds" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item :label="t('rule.formPriority')">
              <el-input-number v-model="form.priority" :min="0" class="rule-config__full" />
            </el-form-item>
            <el-form-item :label="t('rule.formEnabled')">
              <el-switch v-model="form.enabled" />
            </el-form-item>
            <div class="rule-config__form-actions">
              <el-button @click="resetForm">{{ t('common.button.reset') }}</el-button>
              <el-button type="primary" :loading="saving" @click="submitForm">
                {{ editingRuleId === null ? t('common.button.create') : t('common.button.save') }}
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
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import { createRule, deleteRule, listRois, listRules, listScenes, updateRule } from '@/api/resources';
import type { Roi, Rule, RuleCreatePayload, RuleThresholdConfig, RuleType, Scene } from '@/api/types';

const { t } = useI18n();

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
      rule_type: 'obstruction_duration',
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
    return t('rule.allScene');
  }
  return rois.value.find((roi) => roi.id === roiId)?.name ?? `${t('common.table.roi')} #${roiId}`;
}

function formatThresholds(config: RuleThresholdConfig): string {
  const labels: Partial<Record<keyof RuleThresholdConfig, string>> = {
    threshold: t('rule.formThreshold'),
    min_area: t('rule.formMinArea'),
    max_count: t('rule.formMaxCount'),
    duration_seconds: t('rule.formDurationSeconds'),
  };
  const pairs = Object.entries(config).filter(([, value]) => value !== undefined);
  return pairs.length === 0
    ? t('common.none')
    : pairs.map(([key, value]) => `${labels[key as keyof RuleThresholdConfig] ?? key}: ${value}`).join(', ');
}

async function loadData(): Promise<void> {
  if (!Number.isInteger(cameraId.value)) {
    ElMessage.error(t('rule.toastInvalidId'));
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
    ElMessage.error(t('rule.toastLoadFailed'));
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
      ElMessage.success(t('rule.toastCreated'));
    } else {
      const { camera_id: _cameraId, ...updatePayload } = payloadFromForm();
      const updated = await updateRule(editingRuleId.value, updatePayload);
      rules.value = rules.value.map((rule) => (rule.id === updated.id ? updated : rule));
      ElMessage.success(t('rule.toastUpdated'));
    }
    resetForm();
  } catch {
    ElMessage.error(t('rule.toastSaveFailed'));
  } finally {
    saving.value = false;
  }
}

async function confirmDeleteRule(rule: Rule): Promise<void> {
  try {
    await ElMessageBox.confirm(t('rule.deleteConfirm', { id: rule.id }), t('rule.deleteTitle'), { type: 'warning' });
    await deleteRule(rule.id);
    rules.value = rules.value.filter((item) => item.id !== rule.id);
    ElMessage.success(t('rule.toastDeleted'));
    if (editingRuleId.value === rule.id) {
      resetForm();
    }
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('rule.toastDeleteFailed'));
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
