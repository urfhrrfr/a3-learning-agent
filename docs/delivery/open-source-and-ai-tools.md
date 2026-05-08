# 开源组件与 AI 工具说明

## 开源组件

| 组件 | 用途 | 协议 |
| --- | --- | --- |
| Python | 后端运行环境 | PSF License |
| FastAPI | REST API 与 Swagger | MIT |
| Pydantic | 数据校验与 Schema | MIT |
| Uvicorn | ASGI 服务 | BSD |
| SQLite | 本地数据持久化 | Public Domain |
| Pytest | 后端测试 | MIT |
| Vue 3 | 前端框架 | MIT |
| Vite | 前端构建工具 | MIT |
| Pinia | 前端状态管理 | MIT |
| Vue Router | 前端路由 | MIT |
| Mermaid | 思维导图渲染 | MIT |

版本以 `backend/requirements.txt` 和 `frontend/package.json` 为准。

## AI Coding 工具使用说明

开发过程中使用 AI Coding Agent 辅助阅读文档、生成项目骨架、补齐 Mock 流程、编写测试和交付文档。人工应在提交前复核业务逻辑、依赖协议、演示材料和安全边界。

## 大模型和科大讯飞说明

当前 MVP 使用 MockLLMProvider，不依赖真实 API Key。若后续接入科大讯飞模型或平台能力，具体模型、鉴权方式、价格和协议均以官方文档为准。
