import type { App } from "vue";
import { createPinia } from "pinia";

export function setupStore(app: App) {
  app.use(createPinia());
}

export * from "./app";
