<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("recipes.title") }}</h2>
      </div>
      <el-button type="primary" @click="loadData">{{ t("common.refresh") }}</el-button>
    </div>

    <el-alert
      v-if="disabled"
      type="warning"
      show-icon
      :closable="false"
      title="Knowledge system is disabled. Enable knowledge.enabled in config.yaml."
      style="margin-bottom: 12px"
    />

    <el-table :data="recipes" stripe border>
      <el-table-column prop="project_type" :label="t('recipes.projectType')" min-width="140" />
      <el-table-column prop="language" :label="t('recipes.language')" width="100" />
      <el-table-column prop="build_tool" :label="t('recipes.buildTool')" width="120" />
      <el-table-column prop="framework" :label="t('recipes.framework')" min-width="120" />
      <el-table-column prop="confidence" :label="t('recipes.confidence')" width="100">
        <template #default="{ row }">{{ (row.confidence * 100).toFixed(0) }}%</template>
      </el-table-column>
      <el-table-column prop="success_count" :label="t('recipes.success')" width="90" />
      <el-table-column prop="failure_count" :label="t('recipes.failure')" width="90" />
      <el-table-column prop="known_issues_count" :label="t('recipes.issues')" width="100" />
      <el-table-column :label="t('common.actions')" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row.project_type)">{{ t("common.detail") }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawerVisible" :title="detailTitle" size="520px">
      <pre class="detail-json">{{ detailJson }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import KnowledgeAPI from "@/api/knowledge";
import type { BuildRecipeSummary } from "@/api/types";

defineOptions({ name: "Recipes" });

const { t } = useI18n();
const loading = ref(false);
const disabled = ref(false);
const recipes = ref<BuildRecipeSummary[]>([]);
const drawerVisible = ref(false);
const detailTitle = ref("");
const detailJson = ref("");

async function loadData() {
  loading.value = true;
  disabled.value = false;
  try {
    const data = await KnowledgeAPI.listRecipes();
    recipes.value = data.recipes;
  } catch (error: unknown) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 503) disabled.value = true;
  } finally {
    loading.value = false;
  }
}

async function openDetail(projectType: string) {
  detailTitle.value = projectType;
  const data = await KnowledgeAPI.getRecipe(projectType);
  detailJson.value = JSON.stringify(data, null, 2);
  drawerVisible.value = true;
}

onMounted(loadData);
</script>

<style scoped lang="scss">
.detail-json {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, monospace;
  font-size: 12px;
}
</style>
