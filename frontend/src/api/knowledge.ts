import http from "@/utils/request";
import type { BuildInsights, BuildPlan, BuildRecipeSummary, DetectResult, RepoLearningSummary } from "./types";

const KnowledgeAPI = {
  listRecipes() {
    return http.get<unknown, { recipes: BuildRecipeSummary[]; total: number }>("/api/v1/knowledge/recipes");
  },
  getRecipe(projectType: string) {
    return http.get<unknown, Record<string, unknown>>(`/api/v1/knowledge/recipes/${projectType}`);
  },
  listRepoLearnings() {
    return http.get<unknown, { repos: RepoLearningSummary[]; total: number }>("/api/v1/knowledge/repos");
  },
  getRepoLearning(repoId: string) {
    return http.get<unknown, Record<string, unknown>>(`/api/v1/knowledge/repos/${repoId}`);
  },
  detect(repoId: string) {
    return http.post<unknown, DetectResult>(`/api/v1/detect/${repoId}`);
  },
  plan(repoId: string) {
    return http.post<unknown, BuildPlan>(`/api/v1/plan/${repoId}`);
  },
  getInsights() {
    return http.get<unknown, BuildInsights>("/api/v1/insights");
  },
  getInsightsText() {
    return http.get<unknown, { report: string }>("/api/v1/insights/text");
  },
};

export default KnowledgeAPI;
