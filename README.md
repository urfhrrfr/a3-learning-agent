# A3 个性化学习资源生成多智能体系统

面向“人工智能导论”课程的 Python + Vue 参赛作品。系统围绕学习画像、资源生成、Agent Trace、学习路径、智能辅导和练习评估，形成一个可演示、可复现、可扩展的个性化学习闭环。

## 核心亮点

- 多智能体协作：ProfileAgent、KnowledgeAgent、PlannerAgent、资源生成 Agent、ReviewAgent、AssessmentAgent 等按依赖关系协同执行。
- 个性化学习闭环：从画像诊断到资源生成、路径推荐、智能辅导、练习评估和路径调整。
- LLM Provider 抽象：默认使用 Mock 稳定演示，也可切换到星火、DeepSeek、Qwen、OpenAI 兼容接口。
- SQLite 持久化：保存画像、任务、资源、学习路径、评估报告和 Agent Trace，便于本地复现。
- Redis 可选增强：用于任务进度和 Agent Trace 快照缓存；未配置时自动降级，不影响演示。
- 学生使用型前端：主界面聚焦今日任务、学习资料、智能导师和练习反馈，技术细节沉淀到文档与源码。

## 技术栈

- 后端：FastAPI、Pydantic、SQLite、可选 Redis
- 前端：Vue 3、Vite、Pinia、TypeScript
- 模型接入：MockLLMProvider、SparkLLMProvider、OpenAICompatibleProvider

## 本地启动

后端：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
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

提交版本默认不依赖真实模型 Key 和 Redis：

```env
LLM_PROVIDER=mock
REDIS_URL=
```

如需演示真实模型，可参考 `.env.example` 配置 `LLM_PROVIDER=deepseek`、`qwen`、`dashscope`、`spark` 或 `openai_compatible`。

如需启用 Redis：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

Redis 未配置或不可用时，系统会自动使用 SQLite + 内存状态运行。

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
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

当前结果：`28 passed`

前端构建：

```bash
cd frontend
npm run build
```

## 交付文档

- API 契约：`docs/api-contract.md`
- LLM Provider 接入：`docs/llm-provider.md`
- Redis 可选缓存：`docs/redis-cache.md`
- 演示 Runbook：`docs/delivery/demo-runbook.md`
- 7 分钟演示脚本：`docs/delivery/demo-video-script.md`
- PPT 大纲：`docs/delivery/ppt-outline.md`
- 答辩手册：`docs/delivery/presentation-and-defense-guide.md`
- 最终检查清单：`docs/delivery/final-checklist.md`
- 提交说明：`docs/delivery/submission-summary.md`

## 答辩表述建议

本项目提交版采用 SQLite 保证零部署可复现，同时提供 Redis 可选缓存层提升任务状态同步能力。多智能体共享统一 LLM Provider，通过不同角色、提示词、输入上下文和执行顺序完成协作。默认 Mock 模式保证演示稳定，接入真实模型时可通过环境变量平滑切换。
