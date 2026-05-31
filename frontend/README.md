# BuildClaw Frontend

基于 Vue 3 + Vite + Element Plus 的 BuildClaw 运维控制台，参考 vue3-element-admin 的项目结构实现。

## 功能页面

- 仪表盘：运行概览、就绪检查、仓库摘要
- 运行状态：`/readyz` 探针详情
- 仓库规则：分支匹配与部署步骤
- 构建配方 / 仓库学习：知识库数据
- 环境检测 / 构建计划：智能构建 API
- 构建洞察：成功率分析与建议

## 开发

```bash
cd frontend
npm install
npm run dev
```

默认开发端口 `5173`，API 代理到 `http://127.0.0.1:8080`。

请先启动后端：

```bash
cd backend
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## 构建

```bash
npm run build
```

产物输出到 `frontend/dist/`。

## 环境变量

| 变量 | 说明 |
|------|------|
| `VITE_APP_PORT` | 开发服务器端口 |
| `VITE_APP_BASE_API` | API 前缀（开发环境默认 `/dev-api`） |
| `VITE_APP_API_URL` | 后端地址 |
