<template>
  <div v-loading="loading" class="page-container">
    <div class="page-toolbar">
      <div>
        <h2 style="margin: 0">{{ t("insights.title") }}</h2>
      </div>
      <div>
        <el-button @click="loadTextReport">{{ t("insights.textReport") }}</el-button>
        <el-button type="primary" @click="loadData">{{ t("common.refresh") }}</el-button>
      </div>
    </div>

    <el-alert
      v-if="disabled"
      type="warning"
      show-icon
      :closable="false"
      title="Knowledge system is disabled. Enable knowledge.enabled in config.yaml."
    />

    <template v-else-if="insights">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="label">{{ t("insights.overallSuccess") }}</div>
          <div class="value">{{ (insights.overall_success_rate * 100).toFixed(1) }}%</div>
        </div>
        <div class="stat-card">
          <div class="label">{{ t("insights.totalBuilds") }}</div>
          <div class="value">{{ insights.total_builds_tracked }}</div>
        </div>
        <div class="stat-card">
          <div class="label">{{ t("dashboard.recipes") }}</div>
          <div class="value">{{ insights.total_recipes }}</div>
        </div>
        <div class="stat-card">
          <div class="label">{{ t("dashboard.learnings") }}</div>
          <div class="value">{{ insights.total_repo_learnings }}</div>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <el-card class="page-card" shadow="never">
            <template #header>{{ t("insights.recipeInsights") }}</template>
            <div ref="recipeChartRef" class="chart-box" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="12">
          <el-card class="page-card" shadow="never">
            <template #header>{{ t("insights.repoInsights") }}</template>
            <div ref="repoChartRef" class="chart-box" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="8">
          <el-card class="page-card" shadow="never">
            <template #header>{{ t("insights.failurePatterns") }}</template>
            <el-empty v-if="!insights.top_failure_patterns.length" :description="t('common.noData')" />
            <ul v-else class="list-block">
              <li v-for="item in insights.top_failure_patterns" :key="item">{{ item }}</li>
            </ul>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card class="page-card" shadow="never">
            <template #header>{{ t("insights.coverageGaps") }}</template>
            <el-empty v-if="!insights.coverage_gaps.length" :description="t('common.noData')" />
            <ul v-else class="list-block">
              <li v-for="item in insights.coverage_gaps" :key="item">{{ item }}</li>
            </ul>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card class="page-card" shadow="never">
            <template #header>{{ t("insights.recommendations") }}</template>
            <el-empty v-if="!insights.recommendations.length" :description="t('common.noData')" />
            <ul v-else class="list-block">
              <li v-for="item in insights.recommendations" :key="item">{{ item }}</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-dialog v-model="textDialogVisible" :title="t('insights.textReport')" width="760px">
      <pre class="text-report">{{ textReport }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import KnowledgeAPI from "@/api/knowledge";
import type { BuildInsights } from "@/api/types";

type RecipeInsight = BuildInsights["recipe_insights"][number];
type RepoInsight = BuildInsights["repo_insights"][number];

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

defineOptions({ name: "Insights" });

const { t } = useI18n();
const loading = ref(false);
const disabled = ref(false);
const insights = ref<BuildInsights | null>(null);
const textDialogVisible = ref(false);
const textReport = ref("");
const recipeChartRef = ref<HTMLElement>();
const repoChartRef = ref<HTMLElement>();

let recipeChart: echarts.ECharts | null = null;
let repoChart: echarts.ECharts | null = null;

function renderCharts() {
  if (!insights.value) return;

  if (recipeChartRef.value) {
    recipeChart ||= echarts.init(recipeChartRef.value);
    recipeChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 16, top: 24, bottom: 40 },
      xAxis: {
        type: "category",
        data: insights.value.recipe_insights.map((item: RecipeInsight) => item.project_type),
        axisLabel: { rotate: 30 },
      },
      yAxis: { type: "value", max: 100 },
      series: [
        {
          type: "bar",
          data: insights.value.recipe_insights.map((item: RecipeInsight) =>
            Number((item.success_rate * 100).toFixed(1)),
          ),
          itemStyle: { color: "#0f766e" },
        },
      ],
    });
  }

  if (repoChartRef.value) {
    repoChart ||= echarts.init(repoChartRef.value);
    repoChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 16, top: 24, bottom: 40 },
      xAxis: {
        type: "category",
        data: insights.value.repo_insights.map((item: RepoInsight) => item.repository_id),
        axisLabel: { rotate: 30 },
      },
      yAxis: { type: "value", max: 100 },
      series: [
        {
          type: "bar",
          data: insights.value.repo_insights.map((item: RepoInsight) =>
            Number((item.health_score * 100).toFixed(1)),
          ),
          itemStyle: { color: "#2563eb" },
        },
      ],
    });
  }
}

async function loadData() {
  loading.value = true;
  disabled.value = false;
  try {
    insights.value = await KnowledgeAPI.getInsights();
    await nextTick();
    renderCharts();
  } catch (error: unknown) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 503) disabled.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadTextReport() {
  const data = await KnowledgeAPI.getInsightsText();
  textReport.value = data.report;
  textDialogVisible.value = true;
}

function handleResize() {
  recipeChart?.resize();
  repoChart?.resize();
}

onMounted(() => {
  loadData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  recipeChart?.dispose();
  repoChart?.dispose();
});
</script>

<style scoped lang="scss">
.chart-box {
  width: 100%;
  height: 320px;
}

.list-block {
  margin: 0;
  padding-left: 18px;

  li {
    margin-bottom: 8px;
  }
}

.text-report {
  margin: 0;
  max-height: 60vh;
  overflow: auto;
  white-space: pre-wrap;
  font-family: Consolas, monospace;
  font-size: 12px;
}
</style>
