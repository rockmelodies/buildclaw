import { createApp } from "vue";
import App from "./App.vue";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "@/styles/index.scss";
import { setupRouter } from "@/router";
import { setupStore } from "@/stores";
import { setupI18n } from "@/lang";
import * as ElementPlusIcons from "@element-plus/icons-vue";

const app = createApp(App);

setupI18n(app);
setupRouter(app);
setupStore(app);

Object.entries(ElementPlusIcons).forEach(([name, component]) => {
  app.component(name, component);
});

app.mount("#app");
