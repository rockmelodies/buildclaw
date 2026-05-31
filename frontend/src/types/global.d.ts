/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

declare global {
  const ElMessage: typeof import("element-plus")["ElMessage"];
  const ElMessageBox: typeof import("element-plus")["ElMessageBox"];
  const ElNotification: typeof import("element-plus")["ElNotification"];
}

export {};
