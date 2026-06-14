<template>
  <section class="page-card rule-config">
    <el-page-header :icon="null" @back="goBackToCamera">
      <template #content>
        <span>{{ t('rule.title') }} — {{ t('common.table.cameraId') }} {{ cameraId }}</span>
      </template>
    </el-page-header>
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
            <template #default="{ row }">{{ formatConfig(row.config) }}</template>
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
        <el-card shadow="never" :class="{ 'rule-config__form--editing': editingRuleId !== null }">
          <template #header>{{ editingRuleId === null ? t('rule.createRuleTitle') : t('rule.editRuleTitle', { id: editingRuleId }) }}</template>
          <el-form label-position="top" :model="form">
            <el-form-item :label="t('rule.formRuleType')">
              <el-select v-model="form.rule_type" class="rule-config__full" @change="onRuleTypeChange">
                <el-option :label="t('common.enum.ruleType.obstruction_duration')" value="obstruction_duration" />
                <el-option :label="t('common.enum.ruleType.obstruction_area')" value="obstruction_area" />
                <el-option :label="t('common.enum.ruleType.forbidden_zone')" value="forbidden_zone" />
                <el-option :label="t('common.enum.ruleType.fire_smoke')" value="fire_smoke" />
                <el-option :label="t('common.enum.ruleType.litter')" value="litter" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('rule.formRoi')">
              <el-select v-model="form.roi_id" class="rule-config__full" clearable :placeholder="t('rule.phRoi')">
                <el-option v-for="roi in rois" :key="roi.id" :label="roi.name" :value="roi.id" />
              </el-select>
            </el-form-item>

            <!-- obstruction_duration -->
            <template v-if="form.rule_type === 'obstruction_duration'">
              <el-form-item :label="t('rule.formThreshold')">
                <el-input-number v-model="form.config.threshold" :min="0" :step="0.05" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formMinStaySeconds')">
                <el-input-number v-model="form.config.min_stay_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formCooldownSeconds')">
                <el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
            </template>

            <!-- obstruction_area -->
            <template v-else-if="form.rule_type === 'obstruction_area'">
              <el-form-item :label="t('rule.formThresholdRatio')">
                <el-input-number v-model="form.config.threshold_ratio" :min="0" :step="0.01" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formMinDuration')">
                <el-input-number v-model="form.config.min_duration_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formCooldownSeconds')">
                <el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
            </template>

            <!-- forbidden_zone -->
            <template v-else-if="form.rule_type === 'forbidden_zone'">
              <el-form-item :label="t('rule.formMinStaySeconds')">
                <el-input-number v-model="form.config.min_stay_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formCooldownSeconds')">
                <el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
            </template>

            <!-- fire_smoke -->
            <template v-else-if="form.rule_type === 'fire_smoke'">
              <el-form-item :label="t('rule.formConfidenceThreshold')">
                <el-input-number v-model="form.config.confidence_threshold" :min="0" :max="1" :step="0.05" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formMinAreaRatio')">
                <el-input-number v-model="form.config.min_area_ratio" :min="0" :step="0.005" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formCooldownSeconds')">
                <el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
            </template>

            <!-- litter -->
            <template v-else-if="form.rule_type === 'litter'">
              <el-form-item :label="t('rule.formConfidenceThreshold')">
                <el-input-number v-model="form.config.min_confidence" :min="0" :max="1" :step="0.05" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formMinAreaRatio')">
                <el-input-number v-model="form.config.min_area_ratio" :min="0" :step="0.005" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formDurationSeconds')">
                <el-input-number v-model="form.config.duration_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
              <el-form-item :label="t('rule.formCooldownSeconds')">
                <el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-config__full" />
              </el-form-item>
            </template>

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
import { useRoute, useRouter } from 'vue-router';

import { createRule, deleteRule, listRois, listRules, listScenes, updateRule } from '@/api/resources';
import type { Roi, Rule, RuleCreatePayload, RuleType, Scene } from '@/api/types';

const { t } = useI18n();

interface RuleForm {
  rule_type: RuleType;
  roi_id: number | null;
  config: Record<string, number>;
  priority: number;
  enabled: boolean;
}

const DEFAULT_CONFIGS: Record<RuleType, Record<string, number>> = {
  obstruction_duration: { threshold: 3000, min_stay_seconds: 2, cooldown_seconds: 60 },
  obstruction_area: { threshold_ratio: 0.05, min_duration_seconds: 10, cooldown_seconds: 30 },
  forbidden_zone: { min_stay_seconds: 5, cooldown_seconds: 60 },
  fire_smoke: { confidence_threshold: 0.5, min_area_ratio: 0.01, cooldown_seconds: 30 },
  litter: { min_confidence: 0.35, min_area_ratio: 0.005, duration_seconds: 10, cooldown_seconds: 30 },
};

const CONFIG_LABEL_KEYS: Record<string, string> = {
  threshold: 'rule.formThreshold',
  min_stay_seconds: 'rule.formMinStaySeconds',
  cooldown_seconds: 'rule.formCooldownSeconds',
  threshold_ratio: 'rule.formThresholdRatio',
  min_duration_seconds: 'rule.formMinDuration',
  confidence_threshold: 'rule.formConfidenceThreshold',
  min_area_ratio: 'rule.formMinAreaRatio',
  duration_seconds: 'rule.formDurationSeconds',
  min_confidence: 'rule.formConfidenceThreshold',
};

const route = useRoute();
const router = useRouter();
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
    config: { ...DEFAULT_CONFIGS.obstruction_duration },
    priority: 1,
    enabled: true,
  };
}

function onRuleTypeChange(): void {
  form.config = { ...DEFAULT_CONFIGS[form.rule_type] };
}

function resetForm(): void {
  editingRuleId.value = null;
  Object.assign(form, defaultForm());
}

function openCreateForm(): void {
  resetForm();
}

function openEditForm(rule: Rule): void {
  editingRuleId.value = rule.id;
  form.rule_type = rule.rule_type;
  form.roi_id = rule.roi_id;
  form.config = { ...rule.config };
  form.priority = rule.priority;
  form.enabled = rule.enabled;
}

function payloadFromForm(): RuleCreatePayload {
  return {
    camera_id: cameraId.value,
    rule_type: form.rule_type,
    roi_id: form.roi_id,
    config: { ...form.config },
    priority: form.priority,
    enabled: form.enabled,
  };
}

function roiName(roiId: number | null): string {
  if (roiId === null) return t('rule.allScene');
  return rois.value.find((roi) => roi.id === roiId)?.name ?? `${t('common.table.roi')} #${roiId}`;
}

function formatConfig(config: Record<string, number>): string {
  const entries = Object.entries(config).filter(([, v]) => v !== undefined && v !== null);
  if (entries.length === 0) return t('common.none');
  return entries
    .map(([key, value]) => `${t(CONFIG_LABEL_KEYS[key] ?? key)}: ${value}`)
    .join(', ');
}

function goBackToCamera(): void {
  void router.push(`/cameras/${cameraId.value}`);
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
    await ElMessageBox.confirm(t('rule.deleteConfirm', { id: rule.id }), t('rule.deleteTitle'), { type: 'warning', confirmButtonText: t('common.button.confirm'), cancelButtonText: t('common.button.cancel') });
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

.rule-config__form--editing {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
}

.rule-config__form-actions {
  justify-content: flex-end;
}
</style>
