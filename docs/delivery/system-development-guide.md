# 系统开发说明书

## 项目背景与需求

本项目面向高校课程学习场景，解决学生基础差异大、资源匹配粗放、学习路径缺少反馈闭环的问题。MVP 选择“人工智能导论”作为样例课程，通过对话式画像、多智能体协作和资源生成，完成从诊断到练习评估的闭环。

## 总体架构

系统采用 Vue 3 前端、FastAPI 后端、SQLite 本地持久化和 MockLLMProvider。后端提供统一 `{ ok, data, error }` 响应结构，前端通过 REST 调用核心接口，并用轮询式进度展示生成过程。

## 多智能体设计

资源生成流程包含 KnowledgeAgent、PlannerAgent、LectureAgent、MindMapAgent、QuizAgent、ReadingAgent、MediaAgent、CodeCaseAgent 和 ReviewAgent。每个 Agent 产生 AgentTrace，记录输入摘要、输出摘要、来源引用、置信度和状态。AssessmentAgent 负责练习评估后的画像与路径调整。

## 学习画像设计

画像包含专业层次、课程章节、知识基础、学习目标、认知风格、偏好模态、时间预算、弱点、错因模式、兴趣方向和掌握度。画像通过对话增量更新，并保留版本号。

## 资源生成与 RAG

课程知识库采用 `backend/data/courses/ai_intro` 目录，包含 12 章结构化材料、60 道题目草案和 3 个 Python 实操案例。生成资源时写入 `source_refs`，前端展示来源 ID，避免内容变成无依据文本。

## 防幻觉与安全

ReviewAgent 检查来源、难度匹配和敏感内容，输出 `passed`、`needs_revision` 或 `blocked`。对无法确认的事实，系统应提示“该内容需要教师或资料进一步确认”。MVP 不依赖真实 API Key，避免演示环境泄露密钥。

## 前后端设计

前端页面包括工作台、学习画像、资源生成、资源库、学习路径、智能辅导和练习评估。组件包括 ChatPanel、ProfileInsightPanel、GenerationProgress、AgentTraceTimeline、ResourceCard、MarkdownRenderer、MermaidRenderer、LearningPathTimeline、QuizPlayer 和 AssessmentReport。

## 数据库设计

MVP 使用 SQLite 记录 profile、job、resource、path、assessment 等 JSON payload。后续可替换为 SQLAlchemy/SQLModel 实体表，不影响 API 契约。

## 创新点

- 对话式动态画像而非静态表单。
- 多 Agent 可观察协作过程。
- 6 类资源同时生成并带来源和审核状态。
- 练习结果反向更新画像和学习路径。
- MockLLMProvider 保证无真实模型 Key 时可完整演示。
