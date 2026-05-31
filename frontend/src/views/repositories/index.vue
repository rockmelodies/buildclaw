<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("repositories.title") }}</h2>
      </div>
      <el-button type="primary" @click="loadData">{{ t("common.refresh") }}</el-button>
    </div>

    <el-empty v-if="!repositories.length" :description="t('common.noData')" />
    <el-collapse v-else accordion>
      <el-collapse-item v-for="repo in repositories" :key="repo.id" :name="repo.id">
        <template #title>
          <div class="repo-title">
            <strong>{{ repo.name }}</strong>
            <el-tag size="small">{{ repo.id }}</el-tag>
          </div>
        </template>

        <el-descriptions :column="1" border>
          <el-descriptions-item :label="t('repositories.gitUrl')">
            <span class="mono">{{ repo.git_url }}</span>
          </el-descriptions-item>
          <el-descriptions-item :label="t('repositories.webhook')">
            <span class="mono">{{ repo.webhook_path }}</span>
          </el-descriptions-item>
          <el-descriptions-item :label="t('repositories.auth')">
            <el-tag :type="repo.has_https_token ? 'success' : 'info'" size="small">
              {{ t("repositories.httpsToken") }}: {{ repo.has_https_token ? "✓" : "-" }}
            </el-tag>
            <el-tag :type="repo.has_ssh_key ? 'success' : 'info'" size="small" style="margin-left: 8px">
              {{ t("repositories.sshKey") }}: {{ repo.has_ssh_key ? "✓" : "-" }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="rules-block">
          <h4>{{ t("repositories.branchRules") }}</h4>
          <el-table :data="repo.branch_rules" size="small" border>
            <el-table-column prop="pattern" label="Pattern" width="160" />
            <el-table-column prop="worktree" label="Worktree" min-width="180" show-overflow-tooltip />
            <el-table-column :label="t('repositories.steps')" min-width="280">
              <template #default="{ row }">
                <el-tag
                  v-for="step in row.steps"
                  :key="`${step.name}-${step.plugin}`"
                  size="small"
                  style="margin-right: 6px; margin-bottom: 4px"
                >
                  {{ step.name || step.plugin }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { RepositoryAPI } from "@/api/dashboard";
import type { RepositoryItem } from "@/api/types";

defineOptions({ name: "Repositories" });

const { t } = useI18n();
const loading = ref(false);
const repositories = ref<RepositoryItem[]>([]);

async function loadData() {
  loading.value = true;
  try {
    const data = await RepositoryAPI.list();
    repositories.value = data.repositories;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped lang="scss">
.repo-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rules-block {
  margin-top: 16px;

  h4 {
    margin: 0 0 10px;
  }
}
</style>
