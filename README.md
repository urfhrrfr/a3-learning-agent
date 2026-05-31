# A3 个性化学习资源生成多智能体系统

面向“人工智能导论”课程的 Python + Vue 参赛作品。系统围绕学习画像、资源生成、Agent Trace、学习路径、智能辅导和练习评估，形成一个可演示、可复现、可扩展的个性化学习闭环。

## 核心亮点

- 多智能体协作：ProfileAgent、KnowledgeAgent、PlannerAgent、资源生成 Agent、ReviewAgent、AssessmentAgent 等按依赖关系协同执行。
- 个性化学习闭环：从画像诊断到资源生成、路径推荐、智能辅导、练习评估和路径调整。
- LLM Provider 抽象：默认使用 Mock 稳定演示，也可切换到星火、DeepSeek、Qwen、OpenAI 兼容接口。
- RAG 课程知识库：资源生成和智能辅导会结合课程片段检索、画像偏好和证据引用，减少泛泛回答。
- MySQL 持久化：保存画像、任务、资源、学习路径、评估报告、检索日志和历史版本；SQLite 可作为本地 fallback 与迁移来源。
- Redis 缓存增强：用于任务进度和 Agent Trace 快照缓存；未配置时自动降级，不影响核心接口。
- 学生使用型前端：主界面聚焦今日任务、学习资料、智能导师和练习反馈，技术细节沉淀到文档与源码。

## 技术栈

- 后端：FastAPI、Pydantic、MySQL/SQLite、Redis、可选 Chroma
- 前端：Vue 3、Vite、Pinia、TypeScript
- 模型接入：MockLLMProvider、SparkLLMProvider、OpenAICompatibleProvider

## 本地启动

后端依赖：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

本地 MySQL + Redis：

```powershell
cd backend
docker compose -f docker-compose.storage.yml up -d
.\.venv\Scripts\python.exe scripts\check_mysql_redis.py
```

启动后端：

```bash
cd backend
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端：http://127.0.0.1:5173
- 后端 Swagger：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 默认配置

提交版本默认不依赖真实模型 Key。当前推荐本地持久化使用 MySQL + Redis；如需零外部服务演示，可清空 `MYSQL_URL` 和 `REDIS_URL`，系统会回退到 SQLite + 内存状态。

```env
LLM_PROVIDER=mock
MYSQL_URL=mysql+pymysql://a3:123456@127.0.0.1:3306/a3_learning?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
VECTOR_STORE=memory
```

如需演示真实模型，可参考 `.env.example` 配置 `LLM_PROVIDER=deepseek`、`qwen`、`dashscope`、`spark` 或 `openai_compatible`。

如需启用 Redis：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

Redis 未配置或不可用时，系统会自动使用数据库 + 内存状态运行。MySQL 未配置时，持久化层会使用 `backend/data/app.db`。

## 演示闭环

推荐演示顺序：

1. `/` 今日学习中心：查看今天建议完成的学习任务、薄弱点和最近资料。
2. `/profile` 学习画像：通过自然语言更新学习目标、薄弱点和资源偏好。
3. `/generate` 资源生成：输入学习需求，生成图文讲解、导图、练习、脚本和代码案例。
4. `/resources` 资源库：查看讲解、导图、练习、阅读、视频脚本和代码案例。
5. `/path` 学习路径：按任务清单完成学习、练习和复盘。
6. `/tutor` 智能辅导：结合画像和资源进行问答、弱点确认和练习推荐。
7. `/assessment` 练习评估：提交答案，生成评估报告并调整学习路径。

## 验证命令

后端测试：

```bash
cd backend
.\.venv\Scripts\python.exe scripts\check_mysql_redis.py
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py --verify-only
.\.venv\Scripts\python.exe -m pytest
```

当前结果：`62 passed`

提交包说明：项目按源码方式提交，依赖目录不随作品包提交。后端依赖通过 `pip install -r requirements.txt` 安装，前端依赖通过 `npm install` 安装；`.venv`、`node_modules`、日志、缓存、运行时数据库和临时构建目录均不属于提交内容。

前端构建：

```bash
cd frontend
npm run build
```

## 交付文档

- API 契约：`docs/api-contract.md`
- LLM Provider 接入：`docs/llm-provider.md`
- MySQL / Redis 存储：`docs/mysql-redis-storage.md`
- Redis 可选缓存：`docs/redis-cache.md`
- 演示 Runbook：`docs/delivery/demo-runbook.md`
- 7 分钟演示脚本：`docs/delivery/demo-video-script.md`
- PPT 大纲：`docs/delivery/ppt-outline.md`
- 答辩手册：`docs/delivery/presentation-and-defense-guide.md`
- 最终检查清单：`docs/delivery/final-checklist.md`
- 提交说明：`docs/delivery/submission-summary.md`

## 答辩表述建议

本项目当前采用 MySQL 作为 durable store、Redis 作为缓存层，同时保留 SQLite fallback 和迁移脚本，兼顾演示稳定性与工程部署能力。多智能体共享统一 LLM Provider，通过不同角色、提示词、输入上下文、RAG 课程证据和执行顺序完成协作。默认 Mock 模式保证演示稳定，接入真实模型时可通过环境变量平滑切换。

## 真实模型 Provider 切换

默认 `LLM_PROVIDER=mock` 用于稳定演示；评委或老师如果要验证真实大模型，请在启动后端前把环境变量切到真实 provider。后端会优先读取 `backend/.env`，也可以直接在当前终端设置环境变量。

讯飞星火 WebSocket 直连模式：

```env
LLM_PROVIDER=spark
LLM_TIMEOUT_SECONDS=20
SPARK_APP_ID=your_spark_app_id
SPARK_API_KEY=your_spark_api_key
SPARK_API_SECRET=your_spark_api_secret
SPARK_MODEL=generalv3.5
SPARK_API_URL=wss://spark-api.xf-yun.com/v3.5/chat
```

星火 Ultra / OpenAI-compatible 模式也可以走兼容接口：

```env
LLM_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_API_KEY=your_spark_api_password
OPENAI_COMPATIBLE_BASE_URL=https://spark-api-open.xf-yun.com/v1
OPENAI_COMPATIBLE_MODEL=4.0Ultra
```

启动真实模型模式：

```bash
cd backend
uvicorn app.main:app --reload
```

会调用真实模型的核心接口包括：`/api/profile/chat`、`/api/resources/generate/background`、`/api/tutor/chat`、`/api/quiz/submit`。其中资源生成会在多智能体链路中调用 provider，测验提交会在 AssessmentAgent 和后续路径规划中调用 provider。

fallback 不要删除：当 provider 是 `mock`、真实模型 Key 缺失、网络超时、API 返回错误、返回空内容、返回 JSON/结构不符合契约，或多智能体生成链路异常时，系统会切到本地规则/模板兜底，避免核心接口直接 500。

验证当前不是 mock：访问 `GET /api/health`，确认 `llm_provider` 为 `spark` 或 `openai_compatible` 且 `mock_llm=false`；再调用 `/api/tutor/chat` 或 `/api/resources/generate/background`，响应或 job trace 中的 `llm_provider` 应显示真实 provider。若真实模型失败但接口仍 200，并出现 `used_fallback=true`、`fallback_reason` 或 trace warnings，说明真实 provider 路径已被尝试且 fallback 生效。
