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
      <el-button type="primary" @click="openAssignDialog">{{ t('ruleDef.applyToCamera') }}</el-button>
    </div>

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
      <el-table-column :label="t('common.table.actions')" width="160" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEditAssignment(row)">{{ t('common.button.edit') }}</el-button>
          <el-button type="danger" link @click="confirmDeleteRule(row)">{{ t('common.button.delete') }}</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty-note">{{ t('common.empty.noRules') }}</span>
      </template>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingAssignmentId === null ? t('ruleDef.applyToCamera') : t('common.button.edit')" width="500px" destroy-on-close>
      <el-form label-position="top" :model="assignForm">
        <el-form-item v-if="editingAssignmentId === null" :label="t('ruleDef.selectDefinition')">
          <el-select v-model="assignForm.definition_id" class="rule-config__full" :placeholder="t('ruleDef.selectDefinition')">
            <el-option v-for="def in definitions" :key="def.id" :label="`${def.name} (${t('common.enum.ruleType.' + def.rule_type)})`" :value="def.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="assignForm.definition_id !== null && needsRoi(assignForm.definition_id)" :label="t('rule.formRoi')">
          <el-select v-model="assignForm.roi_id" class="rule-config__full" clearable :placeholder="t('rule.phRoi')">
            <el-option v-for="roi in rois" :key="roi.id" :label="roi.name" :value="roi.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('rule.formPriority')">
          <el-input-number v-model="assignForm.priority" :min="0" class="rule-config__full" />
        </el-form-item>
        <el-form-item :label="t('rule.formEnabled')">
          <el-switch v-model="assignForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.button.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submitAssignment">{{ t('common.button.save') }}</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { createRule, deleteRule, listRois, listRuleDefinitions, listRules, listScenes, updateRule } from '@/api/resources';
import type { Roi, Rule, RuleDefinition } from '@/api/types';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const cameraId = computed(() => Number(route.params.id));
const loading = ref(false);
const saving = ref(false);
const rules = ref<Rule[]>([]);
const definitions = ref<RuleDefinition[]>([]);
const rois = ref<Roi[]>([]);
const dialogVisible = ref(false);
const editingAssignmentId = ref<number | null>(null);

const assignForm = reactive({
  definition_id: null as number | null,
  roi_id: null as number | null,
  priority: 10,
  enabled: true,
});

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

function needsRoi(definitionId: number | null): boolean {
  if (definitionId === null) return false;
  const def = definitions.value.find((d) => d.id === definitionId);
  return def?.rule_type !== 'fire_smoke';
}

function goBackToCamera(): void {
  void router.push(`/cameras/${cameraId.value}`);
}

function roiName(roiId: number | null): string {
  if (roiId === null) return t('rule.allScene');
  return rois.value.find((r) => r.id === roiId)?.name ?? `ROI #${roiId}`;
}

function formatConfig(config: Record<string, number>): string {
  const entries = Object.entries(config).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return t('common.none');
  return entries.map(([key, value]) => `${t(CONFIG_LABEL_KEYS[key] ?? key)}: ${value}`).join(', ');
}

function openAssignDialog(): void {
  if (definitions.value.length === 0) {
    ElMessage.warning(t('ruleDef.noDefinitions'));
    return;
  }
  editingAssignmentId.value = null;
  assignForm.definition_id = null;
  assignForm.roi_id = null;
  assignForm.priority = 10;
  assignForm.enabled = true;
  dialogVisible.value = true;
}

function openEditAssignment(rule: Rule): void {
  editingAssignmentId.value = rule.id;
  assignForm.definition_id = rule.definition_id;
  assignForm.roi_id = rule.roi_id;
  assignForm.priority = rule.priority;
  assignForm.enabled = rule.enabled;
  dialogVisible.value = true;
}

async function loadData(): Promise<void> {
  if (!Number.isInteger(cameraId.value)) {
    ElMessage.error(t('rule.toastInvalidId'));
    return;
  }
  loading.value = true;
  try {
    const [ruleData, defData, sceneData] = await Promise.all([
      listRules(cameraId.value),
      listRuleDefinitions(),
      listScenes(cameraId.value),
    ]);
    rules.value = ruleData;
    definitions.value = defData;
    const roiGroups = await Promise.all(sceneData.map((s) => listRois(s.id)));
    rois.value = roiGroups.flat();
  } catch {
    ElMessage.error(t('rule.toastLoadFailed'));
  } finally {
    loading.value = false;
  }
}

async function submitAssignment(): Promise<void> {
  if (assignForm.definition_id === null && editingAssignmentId.value === null) {
    ElMessage.error(t('ruleDef.selectDefinition'));
    return;
  }
  saving.value = true;
  try {
    if (editingAssignmentId.value === null) {
      const created = await createRule({
        definition_id: assignForm.definition_id!,
        camera_id: cameraId.value,
        roi_id: assignForm.roi_id,
        enabled: assignForm.enabled,
        priority: assignForm.priority,
      });
      rules.value.push(created);
      ElMessage.success(t('rule.toastCreated'));
    } else {
      const updated = await updateRule(editingAssignmentId.value, {
        roi_id: assignForm.roi_id,
        enabled: assignForm.enabled,
        priority: assignForm.priority,
      });
      rules.value = rules.value.map((r) => (r.id === updated.id ? updated : r));
      ElMessage.success(t('rule.toastUpdated'));
    }
    dialogVisible.value = false;
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
    rules.value = rules.value.filter((r) => r.id !== rule.id);
    ElMessage.success(t('rule.toastDeleted'));
  } catch (error: unknown) {
    if (error === 'cancel') return;
    ElMessage.error(t('rule.toastDeleteFailed'));
  }
}

onMounted(() => { void loadData(); });
</script>

<style scoped>
.rule-config__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.rule-config__full { width: 100%; }
</style>
