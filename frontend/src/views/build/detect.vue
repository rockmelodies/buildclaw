<template>
  <div class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("detect.title") }}</h2>
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
          <el-button type="primary" :loading="detecting" :disabled="!selectedRepo || knowledgeDisabled" @click="runDetect">
            {{ t("common.run") }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result" v-loading="detecting" class="page-card" shadow="never">
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="t('recipes.projectType')">{{ result.project_type }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.language')">{{ result.language }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.buildTool')">{{ result.build_tool }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.framework')">{{ result.framework }}</el-descriptions-item>
        <el-descriptions-item label="Runtime">{{ result.runtime_version_hint || "-" }}</el-descriptions-item>
        <el-descriptions-item :label="t('recipes.confidence')">
          {{ (result.confidence * 100).toFixed(0) }}%
        </el-descriptions-item>
      </el-descriptions>

      <div class="section">
        <h4>{{ t("detect.markerFiles") }}</h4>
        <div class="tag-row">
          <el-tag v-for="file in result.marker_files" :key="file" type="info">{{ file }}</el-tag>
        </div>
      </div>

      <div v-if="result.all_detected?.length" class="section">
        <h4>{{ t("detect.allDetected") }}</h4>
        <div class="tag-row">
          <el-tag v-for="item in result.all_detected" :key="item">{{ item }}</el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { RepositoryAPI } from "@/api/dashboard";
import KnowledgeAPI, { isKnowledgeEnabled } from "@/api/knowledge";
import type { DetectResult, RepositoryItem } from "@/api/types";

defineOptions({ name: "Detect" });

const { t } = useI18n();
const repoLoading = ref(false);
const detecting = ref(false);
const repositories = ref<RepositoryItem[]>([]);
const selectedRepo = ref("");
const result = ref<DetectResult | null>(null);
const knowledgeDisabled = ref(false);

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

async function runDetect() {
  if (!selectedRepo.value) return;
  detecting.value = true;
  try {
    result.value = await KnowledgeAPI.detect(selectedRepo.value);
  } finally {
    detecting.value = false;
  }
}

onMounted(async () => {
  await loadRepositories();
  knowledgeDisabled.value = !(await isKnowledgeEnabled());
});
</script>

<style scoped lang="scss">
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
