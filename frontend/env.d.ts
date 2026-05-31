/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_PORT: string;
  readonly VITE_APP_BASE_API: string;
  readonly VITE_APP_API_URL: string;
  readonly VITE_APP_TITLE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
