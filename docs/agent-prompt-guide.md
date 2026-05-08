# Cursor / Trae / Claude Code 开发投喂指南

这份文档用于告诉其他 AI Coding Agent 如何基于本项目文档执行开发。

适用工具：

- Cursor Agent
- Trae Agent
- Claude Code
- 其他支持读取项目文件并修改代码的编码 agent

## 1. 基本原则

不要把一句“根据这些文档把项目做出来”直接丢给 agent。这样容易导致：

- 范围失控
- 前后端接口不一致
- 多智能体只停留在文字描述
- 先写 UI mock，不做真实闭环
- 忘记测试、文档和演示材料

正确方式是：

1. 先让主 agent 阅读 `docs/project-blueprint.md` 和 `docs/agent-execution-pack.md`。
2. 让它确认当前里程碑和文件结构。
3. 每次只分配一个明确任务。
4. 每个任务都要带验收标准。
5. 要求它运行验证命令。
6. 让它在回复中列出改动文件、测试结果、未完成风险。

## 2. 推荐开发顺序

建议按以下顺序派发任务：

1. 项目骨架
2. 后端基础 API 和 Mock 数据
3. 多智能体 Orchestrator
4. 课程知识库样例
5. 前端页面和组件
6. 前后端联调
7. 学习评估和路径调整
8. 文档、PPT 大纲、演示视频脚本
9. 统一测试和修复

不要一开始就要求 agent 同时做完整前端、完整后端、知识库和文档。

## 3. 主 Agent 启动提示词

把下面这段发给主 agent：

```text
你现在负责开发一个比赛项目：A3-基于大模型的个性化资源生成与学习多智能体系统。

请先阅读以下文档：
- docs/project-blueprint.md
- docs/agent-execution-pack.md

目标技术栈：
- 后端：Python 3.11+、FastAPI、Pydantic、SQLite、本地向量库或可替代 Mock 检索
- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router
- 协议：REST + SSE
- 大模型：必须有 MockLLMProvider，不能依赖真实 Key 才能演示

当前任务：
先不要完整实现全部功能。请先搭建项目骨架，使前后端可以启动，并准备最小 Mock 数据闭环。

必须完成：
1. 创建 backend 和 frontend 基础目录。
2. 后端提供 FastAPI 应用和健康检查接口。
3. 前端提供 Vue 应用骨架和基础路由。
4. 保留后续接入多智能体、画像、资源生成、学习路径的目录结构。
5. 写 README 中的启动命令。

验收标准：
- 后端可以启动。
- 前端可以启动或至少 npm build 通过。
- 项目结构清晰。
- 不引入无关复杂依赖。
- 回复中列出改动文件、运行过的命令、结果和剩余风险。
```

## 4. 后端 Agent 提示词

适合 Cursor/Trae/Claude Code 单独负责后端时使用：

```text
你负责本项目的后端实现。

请阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-briefs/backend-agent.md

只修改后端相关文件，除非为了更新 README 的启动命令。

当前任务：
实现 FastAPI 后端基础能力，包括数据模型、API 路由、MockLLMProvider、统一响应格式和 SSE 进度事件。

优先完成这些接口：
- GET /api/health
- POST /api/profile/chat
- GET /api/profile/current
- POST /api/resources/generate
- GET /api/jobs/{job_id}
- GET /api/jobs/{job_id}/events
- GET /api/resources
- GET /api/resources/{resource_id}

要求：
1. 没有真实大模型 Key 时也能完整返回 Mock 结果。
2. 资源生成必须产生 job 和 agent trace。
3. API 返回统一格式：{ ok, data, error }。
4. 为后续 Orchestrator 留出清晰服务层。
5. 添加必要测试。

验收标准：
- 后端启动成功。
- Swagger 可查看接口。
- pytest 通过，或说明未能运行的原因。
- 回复中列出改动文件、测试命令、结果和剩余风险。
```

## 5. 多智能体 Agent 提示词

```text
你负责实现多智能体编排层。

请阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-briefs/orchestrator-agent.md

只修改后端中的 agents、services、schemas 或相关测试文件。

当前任务：
实现轻量多智能体 Orchestrator，使一次资源生成请求能经过多个 agent，并输出可展示的 Agent Trace。

必须实现的 agent：
- ProfileAgent
- KnowledgeAgent
- PlannerAgent
- LectureAgent
- MindMapAgent
- QuizAgent
- ReadingAgent
- MediaAgent
- CodeCaseAgent
- ReviewAgent
- AssessmentAgent

要求：
1. 每个 agent 都有清晰的输入、输出和 trace。
2. Mock 模式下也能生成结构完整的内容。
3. 资源必须包含 type、title、content_format、content、source_refs、difficulty、target_profile、review_status、created_by_agents。
4. ReviewAgent 必须能标记 passed、needs_revision 或 blocked。
5. 单个资源失败不能导致整个任务失败。

验收标准：
- 一次生成任务至少返回 6 类资源。
- Agent Trace 可序列化给前端展示。
- 添加或更新测试覆盖资源生成流程。
- 回复中列出改动文件、测试结果和剩余风险。
```

## 6. 前端 Agent 提示词

```text
你负责 Vue 前端实现。

请阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-briefs/frontend-agent.md

只修改 frontend 目录，除非需要更新接口说明。

当前任务：
实现比赛演示所需的核心页面和组件，并对接后端 Mock API。

必须实现页面：
- /
- /profile
- /generate
- /resources
- /path
- /tutor
- /assessment

必须实现组件：
- ChatPanel
- ProfileInsightPanel
- AgentTraceTimeline
- GenerationProgress
- ResourceCard
- MarkdownRenderer
- MermaidRenderer
- LearningPathTimeline
- QuizPlayer
- AssessmentReport

要求：
1. 生成资源时展示 SSE 或轮询进度。
2. Agent Trace 必须可视化。
3. 资源卡片必须展示类型、难度、来源、审核状态。
4. Markdown 和 Mermaid 要能渲染，失败时要 fallback。
5. 不做营销落地页，第一屏就是学习工作台。

验收标准：
- npm run build 通过。
- 可以用 Mock API 跑完整演示流程。
- 页面无明显错位。
- 回复中列出改动文件、验证命令、结果和剩余风险。
```

## 7. 知识库 Agent 提示词

```text
你负责构建课程知识库样例。

请阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-briefs/knowledge-agent.md

当前任务：
创建“人工智能导论”课程知识库，供系统 RAG 和资源生成使用。

要求：
1. 至少 12 章。
2. 每章包含学习目标、核心概念、重点难点、常见误区、示例讲解、练习题草案、拓展阅读建议、实践任务建议。
3. 至少准备 60 道题目草案。
4. 至少准备 3 个 Python 实操案例主题。
5. 内容适合本科生，不写无法核实的具体事实。

建议目录：
- backend/data/courses/ai_intro/course.yaml
- backend/data/courses/ai_intro/chapters/*.md
- backend/data/courses/ai_intro/examples/*.py

验收标准：
- 文件结构清晰。
- 每章格式一致。
- 可被后端按章节和 chunk 来源引用。
- 回复中列出新增文件和内容覆盖范围。
```

## 8. 文档与演示 Agent 提示词

```text
你负责比赛交付文档、PPT 大纲和演示视频脚本。

请阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-briefs/qa-docs-demo-agent.md

当前任务：
准备初赛提交所需文档和演示材料。

必须输出：
- docs/delivery/system-development-guide.md
- docs/delivery/test-guide.md
- docs/delivery/deployment-guide.md
- docs/delivery/open-source-and-ai-tools.md
- docs/delivery/ppt-outline.md
- docs/delivery/demo-video-script.md

要求：
1. 文档要覆盖需求分析、系统架构、多智能体设计、画像设计、资源生成、RAG、防幻觉、内容安全、测试部署。
2. PPT 大纲控制在 12 页以内。
3. 视频脚本控制在 7 分钟以内。
4. 开源组件和 AI Coding 工具说明要单独列出。
5. 不要凭空写死具体模型协议，涉及科大讯飞模型时标注“以官方文档为准”。

验收标准：
- 文档可直接进入初赛提交包。
- PPT 覆盖评分点。
- 视频脚本能完整展示系统闭环。
- 回复中列出新增文件和剩余需要人工补充的信息。
```

## 9. 联调 Agent 提示词

```text
你负责前后端联调和完整演示闭环验证。

请先阅读：
- docs/project-blueprint.md
- docs/agent-execution-pack.md

当前任务：
验证并修复以下完整流程：

1. 进入学习工作台。
2. 通过画像对话更新学生画像。
3. 发起资源生成。
4. 查看生成进度和 Agent Trace。
5. 查看至少 6 类资源。
6. 生成学习路径。
7. 提交练习答案。
8. 查看评估报告和路径调整。

要求：
1. 优先修复阻断演示的问题。
2. 不做大范围重构。
3. 每个修复都要尽量小。
4. 完成后运行后端测试和前端 build。

验收标准：
- 完整流程可演示。
- 没有明显白屏、接口报错、资源空数据。
- 回复中列出修复内容、验证命令、结果和剩余风险。
```

## 10. Cursor 使用建议

推荐方式：

- 用 Agent 模式。
- 在 prompt 中用 `@docs/project-blueprint.md`、`@docs/agent-execution-pack.md`、`@docs/agent-briefs/...` 显式引用文档。
- 每次只给一个任务。
- 勾选或允许它修改相关目录，不要全仓库自由改。
- 要求它最后运行测试和 build。

Cursor 中可以这样写：

```text
请读取 @docs/project-blueprint.md @docs/agent-execution-pack.md @docs/agent-briefs/backend-agent.md。
你只负责 backend 目录。
按 backend-agent.md 的验收标准实现 Milestone 1 的后端部分。
完成后运行可用测试，并总结改动文件、命令结果、剩余风险。
```

## 11. Trae 使用建议

推荐方式：

- 使用 Builder / Agent 模式。
- 先让 Trae 扫描项目结构。
- 再粘贴对应专项提示词。
- 对复杂任务要求它先给出 5-8 步执行清单，再开始改代码。

Trae 中可以这样写：

```text
先阅读 docs/project-blueprint.md、docs/agent-execution-pack.md 和 docs/agent-briefs/frontend-agent.md。
你负责 frontend 目录。
请先输出一个简短执行清单，然后实现前端核心页面和组件。
不要修改后端逻辑。
完成后运行 npm run build，并报告结果。
```

## 12. Claude Code 使用建议

推荐方式：

- 在项目根目录启动 Claude Code。
- 先投喂主任务，再投喂专项任务。
- 让它使用文件系统读取文档，而不是把所有文档复制进对话。
- 要求它保持小步提交或小步完成。

Claude Code 中可以这样写：

```text
Read docs/project-blueprint.md, docs/agent-execution-pack.md, and docs/agent-briefs/orchestrator-agent.md.

You own only the backend multi-agent orchestration layer. Implement the orchestrator and mock agents required by the brief. Keep the implementation small and testable. Do not modify the frontend.

After implementation, run the relevant backend tests. In the final response, list changed files, verification commands, results, and remaining risks.
```

## 13. 给 Agent 的通用完成报告格式

要求每个 agent 最终按这个格式回复：

```text
完成内容：
- ...

修改文件：
- ...

验证命令：
- ...

验证结果：
- ...

未完成 / 风险：
- ...

下一步建议：
- ...
```

## 14. 常见错误

避免这样发任务：

```text
帮我根据 docs 把整个项目做完。
```

更好的写法：

```text
请阅读 docs/project-blueprint.md、docs/agent-execution-pack.md 和 docs/agent-briefs/backend-agent.md。
你只负责 backend 目录。
当前只实现 Milestone 1 和 Milestone 2 的后端部分。
必须支持 Mock 模式，不能依赖真实模型 Key。
完成后运行测试，并按固定格式报告改动和风险。
```

