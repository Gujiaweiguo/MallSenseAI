<template>
  <section class="page-card rule-def">
    <div class="rule-def__header">
      <div>
        <h2 class="page-title">{{ t('ruleDef.title') }}</h2>
        <p class="page-subtitle">{{ t('ruleDef.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">{{ t('ruleDef.create') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="definitions" row-key="id" stripe>
      <el-table-column prop="name" :label="t('common.table.name')" min-width="180" />
      <el-table-column :label="t('common.table.type')" min-width="150">
        <template #default="{ row }">{{ t('common.enum.ruleType.' + row.rule_type) }}</template>
      </el-table-column>
      <el-table-column prop="description" :label="t('ruleDef.description')" min-width="200" show-overflow-tooltip />
      <el-table-column :label="t('common.table.thresholds')" min-width="220">
        <template #default="{ row }">{{ formatConfig(row.config) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.table.actions')" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">{{ t('common.button.edit') }}</el-button>
          <el-button type="danger" link @click="confirmDelete(row)">{{ t('common.button.delete') }}</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('ruleDef.empty') }}</span>
      </template>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId === null ? t('ruleDef.create') : t('ruleDef.editTitle', { id: editingId })" width="600px" destroy-on-close>
      <el-form label-position="top" :model="form">
        <el-form-item :label="t('common.table.name')" required>
          <el-input v-model="form.name" :placeholder="t('ruleDef.phName')" />
        </el-form-item>
        <el-form-item v-if="editingId === null" :label="t('rule.formRuleType')">
          <el-select v-model="form.rule_type" class="rule-def__full" @change="onTypeChange">
            <el-option :label="t('common.enum.ruleType.obstruction_duration')" value="obstruction_duration" />
            <el-option :label="t('common.enum.ruleType.obstruction_area')" value="obstruction_area" />
            <el-option :label="t('common.enum.ruleType.forbidden_zone')" value="forbidden_zone" />
            <el-option :label="t('common.enum.ruleType.fire_smoke')" value="fire_smoke" />
            <el-option :label="t('common.enum.ruleType.litter')" value="litter" />
          </el-select>
        </el-form-item>
        <el-form-item v-else :label="t('rule.formRuleType')">
          <el-tag>{{ t('common.enum.ruleType.' + form.rule_type) }}</el-tag>
        </el-form-item>

        <template v-if="form.rule_type === 'obstruction_duration'">
          <el-form-item :label="t('rule.formThreshold')"><el-input-number v-model="form.config.threshold" :min="0" :step="0.05" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formMinStaySeconds')"><el-input-number v-model="form.config.min_stay_seconds" :min="0" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formCooldownSeconds')"><el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-def__full" /></el-form-item>
        </template>
        <template v-else-if="form.rule_type === 'obstruction_area'">
          <el-form-item :label="t('rule.formThresholdRatio')"><el-input-number v-model="form.config.threshold_ratio" :min="0" :step="0.01" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formMinDuration')"><el-input-number v-model="form.config.min_duration_seconds" :min="0" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formCooldownSeconds')"><el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-def__full" /></el-form-item>
        </template>
        <template v-else-if="form.rule_type === 'forbidden_zone'">
          <el-form-item :label="t('rule.formMinStaySeconds')"><el-input-number v-model="form.config.min_stay_seconds" :min="0" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formCooldownSeconds')"><el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-def__full" /></el-form-item>
        </template>
        <template v-else-if="form.rule_type === 'fire_smoke'">
          <el-form-item :label="t('rule.formConfidenceThreshold')"><el-input-number v-model="form.config.confidence_threshold" :min="0" :max="1" :step="0.05" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formMinAreaRatio')"><el-input-number v-model="form.config.min_area_ratio" :min="0" :step="0.005" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formCooldownSeconds')"><el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-def__full" /></el-form-item>
        </template>
        <template v-else-if="form.rule_type === 'litter'">
          <el-form-item :label="t('rule.formConfidenceThreshold')"><el-input-number v-model="form.config.min_confidence" :min="0" :max="1" :step="0.05" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formMinAreaRatio')"><el-input-number v-model="form.config.min_area_ratio" :min="0" :step="0.005" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formDurationSeconds')"><el-input-number v-model="form.config.duration_seconds" :min="0" class="rule-def__full" /></el-form-item>
          <el-form-item :label="t('rule.formCooldownSeconds')"><el-input-number v-model="form.config.cooldown_seconds" :min="0" class="rule-def__full" /></el-form-item>
        </template>

        <el-form-item :label="t('ruleDef.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.button.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submit">{{ t('common.button.save') }}</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { createRuleDefinition, deleteRuleDefinition, listRuleDefinitions, updateRuleDefinition } from '@/api/resources';
import type { RuleDefinition, RuleType } from '@/api/types';

const { t } = useI18n();

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

const loading = ref(false);
const saving = ref(false);
const definitions = ref<RuleDefinition[]>([]);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);

const form = reactive({
  name: '',
  rule_type: 'fire_smoke' as RuleType,
  config: { ...DEFAULT_CONFIGS.fire_smoke } as Record<string, number>,
  description: '',
});

function resetForm(): void {
  editingId.value = null;
  form.name = '';
  form.rule_type = 'fire_smoke';
  form.config = { ...DEFAULT_CONFIGS.fire_smoke };
  form.description = '';
}

function openCreate(): void {
  resetForm();
  dialogVisible.value = true;
}

function openEdit(def: RuleDefinition): void {
  editingId.value = def.id;
  form.name = def.name;
  form.rule_type = def.rule_type;
  form.config = { ...def.config };
  form.description = def.description ?? '';
  dialogVisible.value = true;
}

function onTypeChange(): void {
  form.config = { ...DEFAULT_CONFIGS[form.rule_type] };
}

function formatConfig(config: Record<string, number>): string {
  const entries = Object.entries(config).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return t('common.none');
  return entries.map(([key, value]) => `${t(CONFIG_LABEL_KEYS[key] ?? key)}: ${value}`).join(', ');
}

async function loadData(): Promise<void> {
  loading.value = true;
  try {
    definitions.value = await listRuleDefinitions();
  } catch {
    ElMessage.error(t('ruleDef.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

async function submit(): Promise<void> {
  if (!form.name.trim()) {
    ElMessage.error(t('ruleDef.nameRequired'));
    return;
  }
  saving.value = true;
  try {
    if (editingId.value === null) {
      await createRuleDefinition({ name: form.name, rule_type: form.rule_type, config: { ...form.config }, description: form.description || undefined });
      ElMessage.success(t('ruleDef.toastCreated'));
    } else {
      await updateRuleDefinition(editingId.value, { name: form.name, config: { ...form.config }, description: form.description || undefined });
      ElMessage.success(t('ruleDef.toastUpdated'));
    }
    dialogVisible.value = false;
    await loadData();
  } catch {
    ElMessage.error(t('ruleDef.toastSaveFailed'));
  } finally {
    saving.value = false;
  }
}

async function confirmDelete(def: RuleDefinition): Promise<void> {
  try {
    await ElMessageBox.confirm(t('ruleDef.deleteConfirm', { name: def.name }), t('ruleDef.deleteTitle'), { type: 'warning', confirmButtonText: t('common.button.confirm'), cancelButtonText: t('common.button.cancel') });
    await deleteRuleDefinition(def.id);
    ElMessage.success(t('ruleDef.toastDeleted'));
    await loadData();
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('ruleDef.toastDeleteFailed'));
  }
}

onMounted(() => { void loadData(); });
</script>

<style scoped>
.rule-def__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.rule-def__full { width: 100%; }
</style>
