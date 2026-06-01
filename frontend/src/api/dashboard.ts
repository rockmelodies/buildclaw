import http, { type HttpConfig } from "@/utils/request";
import type { DashboardData, RepositoryItem, RuntimeStatus } from "./types";

const DashboardAPI = {
  getDashboard(config?: HttpConfig) {
    return http.get<unknown, DashboardData>("/api/v1/dashboard", config);
  },
  getReadyz(config?: HttpConfig) {
    return http.get<unknown, RuntimeStatus>("/readyz", {
      ...config,
      validateStatus: (status) => status === 200 || status === 503,
    });
  },
  getHealthz(config?: HttpConfig) {
    return http.get<unknown, { status: string }>("/healthz", config);
  },
};

const RepositoryAPI = {
  list(config?: HttpConfig) {
    return http.get<unknown, { repositories: RepositoryItem[]; total: number }>(
      "/api/v1/repositories",
      config,
    );
  },
};

export { DashboardAPI, RepositoryAPI };
