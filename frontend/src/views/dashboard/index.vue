<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("dashboard.title") }}</h2>
        <p class="muted" style="margin: 6px 0 0">
          {{ t("dashboard.lastCheck") }}: {{ lastCheck || "-" }}
        </p>
      </div>
      <el-button type="primary" @click="loadData">{{ t("common.refresh") }}</el-button>
    </div>

    <div class="stat-grid">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="label">{{ card.label }}</div>
        <div class="value" :style="{ color: card.color }">{{ card.value }}</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card class="page-card" shadow="never">
          <template #header>
            <span>{{ t("runtime.title") }}</span>
          </template>
          <el-table :data="runtimeRows" size="small">
            <el-table-column prop="name" :label="t('runtime.checkName')" min-width="160" />
            <el-table-column prop="status" :label="t('runtime.status')" width="120">
              <template #default="{ row }">
                <el-tag :type="row.ok ? 'success' : 'danger'" size="small">
                  {{ row.ok ? t("common.ok") : t("common.issue") }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" :label="t('runtime.detail')" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="page-card" shadow="never">
          <template #header>
            <span>{{ t("repositories.title") }}</span>
          </template>
          <el-empty v-if="!dashboard?.repositories.length" :description="t('common.noData')" />
          <div v-else class="repo-list">
            <div v-for="repo in dashboard.repositories" :key="repo.id" class="repo-item">
              <div class="repo-head">
                <strong>{{ repo.name }}</strong>
                <el-tag size="small">{{ repo.id }}</el-tag>
              </div>
              <div class="muted mono">{{ repo.git_url }}</div>
              <div class="muted">{{ t("dashboard.webhookHint") }}: {{ repo.webhook_path }}</div>
              <div class="rule-tags">
                <el-tag
                  v-for="rule in repo.branch_rules"
                  :key="rule.pattern"
                  type="info"
                  size="small"
                >
                  {{ rule.pattern }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { DashboardAPI } from "@/api/dashboard";
import type { DashboardData, RuntimeCheck } from "@/api/types";

defineOptions({ name: "Dashboard" });

const { t } = useI18n();
const loading = ref(false);
const dashboard = ref<DashboardData | null>(null);
const lastCheck = ref("");

const statCards = computed(() => {
  const summary = dashboard.value?.summary;
  return [
    {
      label: t("dashboard.repositories"),
      value: summary?.repositories ?? 0,
      color: "#0f766e",
    },
    {
      label: t("dashboard.runtime"),
      value: summary?.runtime_ok ? t("common.ok") : t("common.issue"),
      color: summary?.runtime_ok ? "#16a34a" : "#dc2626",
    },
    {
      label: t("dashboard.knowledge"),
      value: summary?.knowledge_enabled ? t("common.enabled") : t("common.disabled"),
      color: summary?.knowledge_enabled ? "#2563eb" : "#64748b",
    },
    {
      label: t("dashboard.recipes"),
      value: summary?.recipe_count ?? 0,
      color: "#7c3aed",
    },
  ];
});

const runtimeRows = computed(() => {
  const checks = dashboard.value?.runtime.checks || {};
  return Object.entries(checks).map(([name, value]) => {
    const check = value as RuntimeCheck;
    return {
      name,
      ok: check.ok !== false,
      detail: describeCheck(name, check),
    };
  });
});

function describeCheck(_name: string, check: RuntimeCheck) {
  if (check.path) return check.path;
  if (check.value) return check.value;
  if (typeof check.count === "number") return String(check.count);
  if (check.note) return check.note;
  if (check.available) {
    const available = Object.entries(check.available)
      .filter(([, ok]) => ok)
      .map(([tool]) => tool);
    return available.length ? available.join(", ") : "-";
  }
  return check.enabled === false ? t("common.disabled") : "-";
}

async function loadData() {
  loading.value = true;
  try {
    dashboard.value = await DashboardAPI.getDashboard();
    lastCheck.value = new Date().toLocaleString();
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped lang="scss">
.repo-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.repo-item {
  padding-bottom: 14px;
  border-bottom: 1px dashed $border-color;

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.repo-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rule-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
</style>
