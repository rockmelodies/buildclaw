<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import zhCn from "element-plus/es/locale/lang/zh-cn";
import en from "element-plus/es/locale/lang/en";
import { useAppStore } from "@/stores/app";

const appStore = useAppStore();

const elementLocale = computed(() => (appStore.locale === "zh-CN" ? zhCn : en));
</script>

<style lang="scss">
html,
body,
#app {
  width: 100%;
  height: 100%;
  margin: 0;
}
</style>
