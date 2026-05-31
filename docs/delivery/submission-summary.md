# 提交说明

本文档用于项目提交、汇报和答辩前快速说明当前版本完成内容、启动方式、验证结果和已知边界。

## 项目概述

A3 个性化学习资源生成多智能体系统面向“人工智能导论”课程，提供从学习画像到资源生成、学习路径、智能辅导和练习评估的完整闭环。

提交版默认使用 `MockLLMProvider` 保证稳定演示，同时保留真实 LLM Provider 接口，可切换到星火、DeepSeek、Qwen、DashScope 或 OpenAI 兼容服务。数据默认持久化到 SQLite，Redis 作为可选缓存增强层。

## 完成内容

### 后端能力

- FastAPI 接口与统一响应结构：`{ ok, data, error }`
- 多智能体 Orchestrator：按画像、知识检索、规划、资源生成、审核、评估的顺序协作
- LLM Provider 抽象：支持 mock、spark、openai_compatible、deepseek、qwen、dashscope
- ReviewAgent 事实校验：真实模型模式下可调用 LLM 辅助复核，失败时使用规则兜底
- SQLite 状态恢复：画像、任务、资源、学习路径和评估报告可持久化
- Redis 可选缓存：任务进度、Agent Trace、资源快照可缓存，读取顺序为内存、Redis、SQLite
- 轻量用户隔离：前端通过 `X-User-Id` 传入匿名用户 ID

### 前端体验

- 今日学习中心：展示今天建议完成的学习任务、当前目标、薄弱点和最近资料
- 学习画像：支持自然语言更新画像并展示融合信息
- 资源生成：支持后台生成、SSE/轮询同步进度，前端用学生能理解的话术展示进度
- 资源库：支持多类型资源查看和反馈
- 学习路径：展示个性化步骤、资源推荐和推荐理由
- 智能辅导：结合画像和资源进行问答、弱点确认和练习推荐
- 练习评估：提交答案后先展示得分、主要薄弱点、补救建议和推荐任务

### 文档材料

- API 契约：`docs/api-contract.md`
- LLM Provider 接入：`docs/llm-provider.md`
- Redis 可选缓存：`docs/redis-cache.md`
- 演示 Runbook：`docs/delivery/demo-runbook.md`
- 7 分钟演示脚本：`docs/delivery/demo-video-script.md`
- PPT 大纲：`docs/delivery/ppt-outline.md`
- 答辩手册：`docs/delivery/presentation-and-defense-guide.md`
- 最终检查清单：`docs/delivery/final-checklist.md`

## 启动方式

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
- Swagger：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 环境变量

默认配置：

```env
LLM_PROVIDER=mock
REDIS_URL=
```

真实模型配置参考 `.env.example`。Redis 可选配置：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

## 验证结果

后端测试：

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

当前结果：`62 passed`

提交包说明：本项目按源码方式提交，依赖安装产物不随作品包提交。后端请通过 `pip install -r requirements.txt` 安装依赖，前端请通过 `npm install` 安装依赖；`.venv`、`node_modules`、日志、缓存、运行时数据库和临时构建目录不属于提交内容。

前端构建：

```bash
cd frontend
npm run build
```

当前结果：构建通过。

## 推荐演示流程

1. 打开 `/` 今日学习中心，说明学生进入系统后能直接看到今天该学什么。
2. 进入 `/profile`，输入学习情况，更新个性化画像。
3. 进入 `/generate`，发起资源生成，展示多模态学习资料和生成进度。
4. 进入 `/resources`，查看讲解、导图、练习、阅读、视频脚本和代码案例。
5. 进入 `/path`，展示学习任务清单和推荐理由。
6. 进入 `/tutor`，提问并展示个性化辅导、弱点确认和练习推荐。
7. 进入 `/assessment`，提交练习并展示评估报告和路径调整。

## 已知边界

- 默认 mock 模式用于稳定演示；真实模型效果取决于外部模型服务、Key 和网络状态。
- Redis 是可选增强项，未启用时系统仍可完整运行。
- 当前是课程 MVP，认证、权限和后台管理可作为后续扩展。
- SQLite 适合提交和演示；生产部署可迁移到 PostgreSQL + Redis。

## 建议提交信息

```text
feat: polish demo-ready multi-agent learning workflow

- add optional Redis cache for generation job snapshots
- expose service capability panel on workspace
- enable ReviewAgent LLM fact-check path
- keep SQLite as default persistent storage
- document startup, validation and submission flow
- clean generated frontend source artifacts
```
