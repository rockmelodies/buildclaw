import http from "@/utils/request";
import type { DashboardData, RepositoryItem } from "./types";

const DashboardAPI = {
  getDashboard() {
    return http.get<unknown, DashboardData>("/api/v1/dashboard");
  },
  getReadyz() {
    return http.get<unknown, import("./types").RuntimeStatus>("/readyz");
  },
  getHealthz() {
    return http.get<unknown, { status: string }>("/healthz");
  },
};

const RepositoryAPI = {
  list() {
    return http.get<unknown, { repositories: RepositoryItem[]; total: number }>("/api/v1/repositories");
  },
};

export { DashboardAPI, RepositoryAPI };
