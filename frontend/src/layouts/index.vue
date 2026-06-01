<template>
  <div class="layout" :class="{ collapsed: appStore.sidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand">
        <img src="/favicon.svg" alt="BuildClaw" class="brand-icon" />
        <div v-show="!appStore.sidebarCollapsed" class="brand-text">
          <strong>{{ t("app.title") }}</strong>
          <span>{{ t("app.subtitle") }}</span>
        </div>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.sidebarCollapsed"
          router
          class="sidebar-menu"
        >
          <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ t(`menu.${item.title}`) }}</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </aside>

    <section class="main">
      <header class="navbar">
        <div class="navbar-left">
          <el-button text @click="appStore.toggleSidebar()">
            <el-icon><Fold v-if="!appStore.sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ t("app.title") }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="navbar-right">
          <el-select :model-value="appStore.locale" size="small" style="width: 110px" @change="handleLocaleChange">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en" />
          </el-select>
          <el-switch
            :model-value="appStore.isDark"
            inline-prompt
            active-text="Dark"
            inactive-text="Light"
            @change="(val) => appStore.setDark(Boolean(val))"
          />
          <el-button type="primary" plain @click="refreshPage">
            <el-icon><Refresh /></el-icon>
            {{ t("common.refresh") }}
          </el-button>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from "@/stores/app";
import i18n from "@/lang";

const route = useRoute();
const appStore = useAppStore();
const { t, locale } = useI18n();

const menuItems = [
  { path: "/dashboard", title: "dashboard", icon: "Odometer" },
  { path: "/runtime", title: "runtime", icon: "Monitor" },
  { path: "/repositories", title: "repositories", icon: "Collection" },
  { path: "/knowledge/recipes", title: "recipes", icon: "Document" },
  { path: "/knowledge/repos", title: "repoLearnings", icon: "DataAnalysis" },
  { path: "/build/detect", title: "detect", icon: "Search" },
  { path: "/build/plan", title: "plan", icon: "SetUp" },
  { path: "/insights", title: "insights", icon: "TrendCharts" },
];

const activeMenu = computed(() => route.path);
const currentTitle = computed(() => {
  const metaTitle = route.meta.title as string | undefined;
  return metaTitle ? t(`menu.${metaTitle}`) : "";
});

function handleLocaleChange(value: "zh-CN" | "en") {
  appStore.setLocale(value);
  locale.value = value;
  i18n.global.locale.value = value;
}

function refreshPage() {
  window.location.reload();
}
</script>

<style scoped lang="scss">
.layout {
  display: flex;
  width: 100%;
  height: 100%;
  background: $bg-color;
}

.sidebar {
  width: $sidebar-width;
  background: var(--el-bg-color);
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.layout.collapsed .sidebar {
  width: 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: $header-height;
  padding: 12px 16px;
  border-bottom: 1px solid $border-color;
}

.brand-icon {
  width: 32px;
  height: 32px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;

  strong {
    font-size: 16px;
    color: $primary-color;
  }

  span {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.3;
  }
}

.menu-scroll {
  flex: 1;
}

.sidebar-menu {
  border-right: none;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.navbar {
  height: $header-height;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--el-bg-color);
  border-bottom: 1px solid $border-color;
}

.navbar-left,
.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content {
  flex: 1;
  overflow: auto;
  padding: $page-padding;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
