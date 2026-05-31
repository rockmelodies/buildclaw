import type { App } from "vue";
import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";
import NProgress from "nprogress";
import "nprogress/nprogress.css";

export const Layout = () => import("@/layouts/index.vue");

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    component: Layout,
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/dashboard/index.vue"),
        meta: { title: "dashboard", icon: "Odometer" },
      },
      {
        path: "runtime",
        name: "Runtime",
        component: () => import("@/views/runtime/index.vue"),
        meta: { title: "runtime", icon: "Monitor" },
      },
      {
        path: "repositories",
        name: "Repositories",
        component: () => import("@/views/repositories/index.vue"),
        meta: { title: "repositories", icon: "Collection" },
      },
      {
        path: "knowledge/recipes",
        name: "Recipes",
        component: () => import("@/views/knowledge/recipes.vue"),
        meta: { title: "recipes", icon: "Document" },
      },
      {
        path: "knowledge/repos",
        name: "RepoLearnings",
        component: () => import("@/views/knowledge/repos.vue"),
        meta: { title: "repoLearnings", icon: "DataAnalysis" },
      },
      {
        path: "build/detect",
        name: "Detect",
        component: () => import("@/views/build/detect.vue"),
        meta: { title: "detect", icon: "Search" },
      },
      {
        path: "build/plan",
        name: "Plan",
        component: () => import("@/views/build/plan.vue"),
        meta: { title: "plan", icon: "SetUp" },
      },
      {
        path: "insights",
        name: "Insights",
        component: () => import("@/views/insights/index.vue"),
        meta: { title: "insights", icon: "TrendCharts" },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/dashboard",
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

NProgress.configure({ showSpinner: false });

router.beforeEach((_to, _from, next) => {
  NProgress.start();
  next();
});

router.afterEach(() => {
  NProgress.done();
});

export function setupRouter(app: App) {
  app.use(router);
}

export default router;
