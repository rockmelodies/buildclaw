import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import { defineConfig, loadEnv } from "vite";

const pathSrc = resolve(import.meta.dirname, "src");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return {
    resolve: {
      alias: {
        "@": pathSrc,
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/styles/variables.scss" as *;`,
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: Number(env.VITE_APP_PORT || 5173),
      open: true,
      proxy: {
        [env.VITE_APP_BASE_API]: {
          changeOrigin: true,
          target: env.VITE_APP_API_URL,
          rewrite: (path) => path.replace(new RegExp(`^${env.VITE_APP_BASE_API}`), ""),
        },
      },
    },
    plugins: [
      vue(),
      AutoImport({
        imports: ["vue", "vue-router", "pinia", "vue-i18n"],
        resolvers: [ElementPlusResolver({ importStyle: "sass" })],
        vueTemplate: true,
        dts: "src/types/auto-imports.d.ts",
      }),
      Components({
        resolvers: [ElementPlusResolver({ importStyle: "sass" })],
        dts: "src/types/components.d.ts",
      }),
    ],
    build: {
      outDir: "dist",
      chunkSizeWarningLimit: 1200,
    },
  };
});
