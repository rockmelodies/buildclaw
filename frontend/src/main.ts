import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "@/styles/index.scss";
import { setupRouter } from "@/router";
import { setupI18n } from "@/lang";
import { useAppStore } from "@/stores/app";
import * as ElementPlusIcons from "@element-plus/icons-vue";

const pinia = createPinia();
const app = createApp(App);

setupI18n(app);
setupRouter(app);
app.use(pinia);

// 挂载前初始化主题，避免闪烁
useAppStore(pinia).initTheme();

Object.entries(ElementPlusIcons).forEach(([name, component]) => {
  app.component(name, component);
});

app.mount("#app");
