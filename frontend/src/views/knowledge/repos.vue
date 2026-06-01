<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("learnings.title") }}</h2>
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

    <el-table :data="repos" stripe border>
      <el-table-column prop="repository_id" :label="t('learnings.repoId')" min-width="160" />
      <el-table-column prop="project_type" :label="t('recipes.projectType')" min-width="140" />
      <el-table-column prop="language" :label="t('recipes.language')" width="100" />
      <el-table-column prop="framework" :label="t('recipes.framework')" min-width="120" />
      <el-table-column prop="total_builds" :label="t('learnings.totalBuilds')" width="110" />
      <el-table-column prop="success_rate" :label="t('learnings.successRate')" width="120">
        <template #default="{ row }">{{ (row.success_rate * 100).toFixed(1) }}%</template>
      </el-table-column>
      <el-table-column prop="last_build_status" :label="t('learnings.lastStatus')" width="120">
        <template #default="{ row }">
          <el-tag :type="row.last_build_status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.last_build_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row.repository_id)">{{ t("common.detail") }}</el-button>
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
import type { RepoLearningSummary } from "@/api/types";
import { isHttpStatus } from "@/utils/request";

defineOptions({ name: "RepoLearnings" });

const { t } = useI18n();
const loading = ref(false);
const disabled = ref(false);
const repos = ref<RepoLearningSummary[]>([]);
const drawerVisible = ref(false);
const detailTitle = ref("");
const detailJson = ref("");

async function loadData() {
  loading.value = true;
  disabled.value = false;
  try {
    const data = await KnowledgeAPI.listRepoLearnings({ silent: true });
    repos.value = data.repos;
  } catch (error: unknown) {
    if (isHttpStatus(error, 503)) {
      disabled.value = true;
      repos.value = [];
    }
  } finally {
    loading.value = false;
  }
}

async function openDetail(repoId: string) {
  detailTitle.value = repoId;
  try {
    const data = await KnowledgeAPI.getRepoLearning(repoId);
    detailJson.value = JSON.stringify(data, null, 2);
    drawerVisible.value = true;
  } catch {
    // 错误提示由 request 拦截器处理
  }
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
