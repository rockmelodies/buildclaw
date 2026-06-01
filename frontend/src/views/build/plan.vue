<template>
  <div class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("plan.title") }}</h2>
        <p class="muted" style="margin: 6px 0 0">{{ t("detect.hint") }}</p>
      </div>
    </div>

    <el-alert
      v-if="knowledgeDisabled"
      type="warning"
      show-icon
      :closable="false"
      title="Knowledge system is disabled. Enable knowledge.enabled in config.yaml."
      style="margin-bottom: 12px"
    />

    <el-card class="page-card" shadow="never">
      <el-form inline>
        <el-form-item :label="t('detect.selectRepo')">
          <el-select v-model="selectedRepo" filterable style="width: 260px" :loading="repoLoading">
            <el-option v-for="repo in repositories" :key="repo.id" :label="repo.name" :value="repo.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="planning" :disabled="!selectedRepo || knowledgeDisabled" @click="runPlan">
            {{ t("common.run") }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="plan" v-loading="planning" class="page-card" shadow="never">
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="t('recipes.projectType')">{{ plan.project_type }}</el-descriptions-item>
        <el-descriptions-item :label="t('plan.source')">{{ plan.plan_source }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.language')">{{ plan.language }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.buildTool')">{{ plan.build_tool }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.framework')">{{ plan.framework }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.confidence')">
          {{ (plan.confidence * 100).toFixed(0) }}%
        </el-descriptions-item>
      </el-descriptions>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col v-for="section in stepSections" :key="section.title" :xs="24" :md="12" :xl="6">
          <div class="step-block">
            <h4>{{ section.title }}</h4>
            <el-empty v-if="!section.steps.length" :description="t('common.noData')" :image-size="48" />
            <ol v-else>
              <li v-for="(step, index) in section.steps" :key="index" class="mono">{{ step }}</li>
            </ol>
          </div>
        </el-col>
      </el-row>

      <div v-if="plan.required_tools?.length" class="section">
        <h4>{{ t("plan.tools") }}</h4>
        <div class="tag-row">
          <el-tag v-for="tool in plan.required_tools" :key="tool">{{ tool }}</el-tag>
        </div>
      </div>

      <div v-if="plan.workarounds?.length" class="section">
        <h4>{{ t("plan.workarounds") }}</h4>
        <ul>
          <li v-for="(item, index) in plan.workarounds" :key="index">{{ item }}</li>
        </ul>
      </div>

      <div v-if="plan.workflow_steps?.length" class="section">
        <h4>Workflow Steps</h4>
        <el-table :data="plan.workflow_steps" size="small" border>
          <el-table-column prop="name" label="Name" />
          <el-table-column prop="plugin" label="Plugin" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { RepositoryAPI } from "@/api/dashboard";
import KnowledgeAPI, { isKnowledgeEnabled } from "@/api/knowledge";
import type { BuildPlan, RepositoryItem } from "@/api/types";

defineOptions({ name: "Plan" });

const { t } = useI18n();
const repoLoading = ref(false);
const planning = ref(false);
const repositories = ref<RepositoryItem[]>([]);
const selectedRepo = ref("");
const plan = ref<BuildPlan | null>(null);
const knowledgeDisabled = ref(false);

const stepSections = computed(() => {
  if (!plan.value) return [];
  return [
    { title: t("plan.install"), steps: plan.value.install_steps || [] },
    { title: t("plan.test"), steps: plan.value.test_steps || [] },
    { title: t("plan.build"), steps: plan.value.build_steps || [] },
    { title: t("plan.deploy"), steps: plan.value.deploy_steps || [] },
  ];
});

async function loadRepositories() {
  repoLoading.value = true;
  try {
    const data = await RepositoryAPI.list();
    repositories.value = data.repositories;
    if (!selectedRepo.value && repositories.value.length) {
      selectedRepo.value = repositories.value[0].id;
    }
  } finally {
    repoLoading.value = false;
  }
}

async function runPlan() {
  if (!selectedRepo.value) return;
  planning.value = true;
  try {
    plan.value = await KnowledgeAPI.plan(selectedRepo.value);
  } finally {
    planning.value = false;
  }
}

onMounted(async () => {
  await loadRepositories();
  knowledgeDisabled.value = !(await isKnowledgeEnabled());
});
</script>

<style scoped lang="scss">
.step-block {
  min-height: 180px;
  padding: 12px;
  border: 1px solid $border-color;
  border-radius: 10px;
  background: var(--el-fill-color-blank);

  h4 {
    margin: 0 0 10px;
  }

  ol {
    margin: 0;
    padding-left: 18px;
  }

  li {
    margin-bottom: 6px;
    font-size: 12px;
  }
}

.section {
  margin-top: 18px;

  h4 {
    margin: 0 0 10px;
  }
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
