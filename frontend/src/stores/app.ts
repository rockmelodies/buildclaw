import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";

export const useAppStore = defineStore("app", () => {
  const locale = useStorage<"zh-CN" | "en">("buildclaw-locale", "zh-CN");
  const sidebarCollapsed = useStorage("buildclaw-sidebar-collapsed", false);
  const isDark = useStorage("buildclaw-dark-mode", false);

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  function toggleDark() {
    isDark.value = !isDark.value;
    document.documentElement.classList.toggle("dark", isDark.value);
  }

  function setLocale(value: "zh-CN" | "en") {
    locale.value = value;
  }

  function initTheme() {
    document.documentElement.classList.toggle("dark", isDark.value);
  }

  return {
    locale,
    sidebarCollapsed,
    isDark,
    toggleSidebar,
    toggleDark,
    setLocale,
    initTheme,
  };
});
