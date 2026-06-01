import http, { type HttpConfig } from "@/utils/request";
import type { BuildInsights, BuildPlan, BuildRecipeSummary, DetectResult, RepoLearningSummary } from "./types";

const KnowledgeAPI = {
  listRecipes(config?: HttpConfig) {
    return http.get<unknown, { recipes: BuildRecipeSummary[]; total: number }>(
      "/api/v1/knowledge/recipes",
      config,
    );
  },
  getRecipe(projectType: string, config?: HttpConfig) {
    return http.get<unknown, Record<string, unknown>>(`/api/v1/knowledge/recipes/${projectType}`, config);
  },
  listRepoLearnings(config?: HttpConfig) {
    return http.get<unknown, { repos: RepoLearningSummary[]; total: number }>(
      "/api/v1/knowledge/repos",
      config,
    );
  },
  getRepoLearning(repoId: string, config?: HttpConfig) {
    return http.get<unknown, Record<string, unknown>>(`/api/v1/knowledge/repos/${repoId}`, config);
  },
  detect(repoId: string, config?: HttpConfig) {
    return http.post<unknown, DetectResult>(`/api/v1/detect/${repoId}`, undefined, config);
  },
  plan(repoId: string, config?: HttpConfig) {
    return http.post<unknown, BuildPlan>(`/api/v1/plan/${repoId}`, undefined, config);
  },
  getInsights(config?: HttpConfig) {
    return http.get<unknown, BuildInsights>("/api/v1/insights", config);
  },
  getInsightsText(config?: HttpConfig) {
    return http.get<unknown, { report: string }>("/api/v1/insights/text", config);
  },
};

export default KnowledgeAPI;

export async function isKnowledgeEnabled(): Promise<boolean> {
  try {
    await KnowledgeAPI.listRecipes({ silent: true });
    return true;
  } catch {
    return false;
  }
}
