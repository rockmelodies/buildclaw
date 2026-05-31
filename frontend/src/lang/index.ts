import type { App } from "vue";
import { createI18n } from "vue-i18n";
import zhCN from "./zh-CN";
import en from "./en";

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem("buildclaw-locale") || "zh-CN",
  fallbackLocale: "zh-CN",
  messages: {
    "zh-CN": zhCN,
    en,
  },
});

export function setupI18n(app: App) {
  app.use(i18n);
}

export default i18n;
