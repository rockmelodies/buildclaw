export interface RuntimeCheck {
  ok: boolean;
  path?: string;
  value?: string;
  count?: number;
  enabled?: boolean;
  writable?: boolean;
  exists?: boolean;
  required?: boolean;
  note?: string;
  available?: Record<string, boolean>;
}

export interface RuntimeStatus {
  ok: boolean;
  checks: Record<string, RuntimeCheck>;
}

export interface BranchRule {
  pattern: string;
  worktree?: string;
  steps: Array<{ name: string; plugin: string; config?: Record<string, unknown> }>;
}

export interface RepositoryItem {
  id: string;
  name: string;
  git_url: string;
  webhook_path: string;
  has_https_token?: boolean;
  has_ssh_key?: boolean;
  branch_rules: BranchRule[];
}

export interface DashboardData {
  version: string;
  summary: {
    repositories: number;
    runtime_ok: boolean;
    knowledge_enabled: boolean;
    recipe_count: number;
    repo_learning_count: number;
  };
  runtime: RuntimeStatus;
  repositories: RepositoryItem[];
  knowledge: {
    enabled: boolean;
    recipe_count?: number;
    repo_learning_count?: number;
    total_builds_tracked?: number;
  };
  config: {
    workspace_root: string;
    knowledge_root: string;
  };
}

export interface BuildRecipeSummary {
  project_type: string;
  language: string;
  build_tool: string;
  framework: string;
  confidence: number;
  success_count: number;
  failure_count: number;
  known_issues_count: number;
}

export interface RepoLearningSummary {
  repository_id: string;
  project_type: string;
  language: string;
  framework: string;
  total_builds: number;
  success_rate: number;
  last_build_status: string;
}

export interface BuildInsights {
  generated_at: string;
  total_recipes: number;
  total_repo_learnings: number;
  total_builds_tracked: number;
  overall_success_rate: number;
  recipe_insights: Array<{
    project_type: string;
    language: string;
    build_tool: string;
    success_rate: number;
    confidence: number;
    known_issues_count: number;
  }>;
  repo_insights: Array<{
    repository_id: string;
    project_type: string;
    health_score: number;
    success_rate: number;
    total_builds: number;
  }>;
  top_failure_patterns: string[];
  coverage_gaps: string[];
  recommendations: string[];
}

export interface DetectResult {
  repository_id: string;
  project_type: string;
  language: string;
  build_tool: string;
  framework: string;
  runtime_version_hint: string;
  confidence: number;
  marker_files: string[];
  all_detected: string[];
}

export interface BuildPlan {
  repository_id: string;
  project_type: string;
  language: string;
  build_tool: string;
  framework: string;
  plan_source: string;
  confidence: number;
  required_tools: string[];
  environment_variables: Record<string, string>;
  install_steps: string[];
  test_steps: string[];
  build_steps: string[];
  deploy_steps: string[];
  workarounds: string[];
  workflow_steps: Array<{ name: string; plugin: string; config: Record<string, unknown> }>;
}
