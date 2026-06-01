import axios, { type AxiosError, type AxiosRequestConfig } from "axios";

declare module "axios" {
  export interface AxiosRequestConfig {
    /** 为 true 时不弹出 ElMessage 错误提示 */
    silent?: boolean;
  }
}

export function formatApiError(error: AxiosError): string {
  const data = error.response?.data as
    | { detail?: unknown; error?: unknown; message?: unknown }
    | undefined;

  if (typeof data?.error === "string") return data.error;
  if (typeof data?.message === "string") return data.message;

  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }

  return error.message || "请求失败";
}

export function isHttpStatus(error: unknown, status: number): boolean {
  return axios.isAxiosError(error) && error.response?.status === status;
}

const http = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API,
  timeout: 60000,
  headers: { "Content-Type": "application/json;charset=utf-8" },
});

http.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    if (!error.config?.silent) {
      ElMessage.error(formatApiError(error));
    }
    return Promise.reject(error);
  },
);

export default http;

export type HttpConfig = AxiosRequestConfig;
