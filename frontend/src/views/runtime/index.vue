<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("runtime.title") }}</h2>
        <p class="muted" style="margin: 6px 0 0">{{ t("runtime.subtitle") }}</p>
      </div>
      <el-tag :type="runtime?.ok ? 'success' : 'danger'" size="large">
        {{ runtime?.ok ? t("common.ok") : t("common.issue") }}
      </el-tag>
    </div>

    <el-card class="page-card" shadow="never">
      <el-table :data="rows" stripe>
        <el-table-column prop="label" :label="t('runtime.checkName')" min-width="180" />
        <el-table-column prop="status" :label="t('runtime.status')" width="140">
          <template #default="{ row }">
            <el-tag :type="row.ok ? 'success' : row.optional ? 'warning' : 'danger'">
              {{ row.statusText }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" :label="t('runtime.detail')" min-width="320">
          <template #default="{ row }">
            <span class="mono">{{ row.detail }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="buildTools.length" class="page-card" shadow="never">
      <template #header>Build Tools</template>
      <div class="tool-grid">
        <el-tag
          v-for="tool in buildTools"
          :key="tool.name"
          :type="tool.available ? 'success' : 'info'"
          effect="plain"
        >
          {{ tool.name }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { DashboardAPI } from "@/api/dashboard";
import type { RuntimeCheck, RuntimeStatus } from "@/api/types";

defineOptions({ name: "Runtime" });

const { t } = useI18n();
const loading = ref(false);
const runtime = ref<RuntimeStatus | null>(null);

const rows = computed(() => {
  const checks = runtime.value?.checks || {};
  return Object.entries(checks)
    .filter(([name]) => name !== "build_tools")
    .map(([name, rawCheck]) => {
      const check = rawCheck as RuntimeCheck;
      return {
        label: humanize(name),
        ok: check.ok !== false,
        optional: check.required === false,
        statusText:
          check.ok !== false
            ? t("common.ok")
            : check.required === false
              ? t("common.optional")
              : t("common.issue"),
        detail: formatCheckDetail(check),
      };
    });
});

const buildTools = computed(() => {
  const available = runtime.value?.checks.build_tools?.available || {};
  return Object.entries(available).map(([name, ok]) => ({ name, available: ok }));
});

function humanize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatCheckDetail(check: RuntimeCheck) {
  if (check.path) return check.path;
  if (check.value) return check.value;
  if (typeof check.count === "number") return `count=${check.count}`;
  if (check.note) return check.note;
  if (check.enabled !== undefined) {
    return [
      check.enabled ? "enabled" : "disabled",
      check.writable !== undefined ? `writable=${check.writable}` : "",
    ]
      .filter(Boolean)
      .join(", ");
  }
  return JSON.stringify(check);
}

async function loadData() {
  loading.value = true;
  try {
    runtime.value = await DashboardAPI.getReadyz();
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped lang="scss">
.tool-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
