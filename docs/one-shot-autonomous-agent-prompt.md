# 一次性自主开发提示词

这份提示词适合直接粘贴到 Cursor、Trae、Claude Code 等 AI Coding Agent 中，让它按项目文档一步一步推进开发。

使用方式：

1. 把整个项目目录打开。
2. 确保 `docs/` 目录存在。
3. 把下面的提示词一次性粘贴给 agent。
4. 让它持续执行，直到完成 MVP 或遇到真实阻塞。

## 一次性提示词

```text
你现在是本项目的主开发 agent，请基于仓库内文档自主推进开发，不要只给计划。

项目背景：
这是“第十五届中国软件杯 A 组赛题：基于大模型的个性化资源生成与学习多智能体系统开发”。目标是开发一个 Python 后端 + Vue 前端的多智能体个性化学习资源生成系统。

请先阅读这些文档：
- docs/README.md
- docs/project-blueprint.md
- docs/agent-execution-pack.md
- docs/agent-prompt-guide.md
- docs/agent-briefs/backend-agent.md
- docs/agent-briefs/orchestrator-agent.md
- docs/agent-briefs/frontend-agent.md
- docs/agent-briefs/knowledge-agent.md
- docs/agent-briefs/qa-docs-demo-agent.md

总目标：
实现一个可本地运行、可演示、可提交初赛的 MVP。必须完成以下闭环：

学生对话输入学习情况
-> 系统抽取并更新学习画像
-> 多智能体协同生成个性化资源
-> 展示生成进度和 Agent Trace
-> 系统生成学习路径并推送资源
-> 学生完成练习
-> 系统评估学习效果并调整画像和路径

技术栈要求：
- 后端：Python 3.11+、FastAPI、Pydantic、SQLite
- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router
- 通信：REST + SSE 或可解释的轮询 fallback
- 大模型：必须实现 MockLLMProvider，不能依赖真实 API Key 才能演示
- 多智能体：实现轻量 Orchestrator，所有 agent 都要产生可展示 trace

重要约束：
1. 不要先做营销页，第一屏必须是学习工作台或可进入核心流程的页面。
2. 不要把系统做成纯聊天机器人，必须展示画像、资源、学习路径、评估报告和 Agent Trace。
3. 不要依赖真实大模型 Key。没有 Key 时必须可以用 Mock 模式跑完整演示。
4. 不要一开始做复杂权限、教师端、班级系统、支付、移动端 App。
5. 不要引入不必要的新依赖。
6. 保持代码结构清晰，优先完成可运行闭环。

请按以下里程碑自主执行。每完成一个里程碑，先运行相关验证命令，修复明显错误，然后继续下一个里程碑。除非遇到破坏性操作或真实信息缺失，不要停下来问我是否继续。

Milestone 1：项目骨架
- 创建 backend 和 frontend 目录。
- 后端建立 FastAPI 应用、健康检查接口、统一响应结构。
- 前端建立 Vue 3 + Vite + TypeScript 应用、基础路由和工作台页面。
- 写清楚 README 启动命令。
- 验收：后端可启动，前端可启动或 build 通过。

Milestone 2：后端基础能力
- 实现基础数据模型和 schema。
- 实现 MockLLMProvider。
- 实现画像接口：
  - POST /api/profile/chat
  - GET /api/profile/current
- 实现资源生成任务接口：
  - POST /api/resources/generate
  - GET /api/jobs/{job_id}
  - GET /api/jobs/{job_id}/events
  - GET /api/resources
  - GET /api/resources/{resource_id}
- 验收：没有真实模型 Key 也能返回结构完整的数据。

Milestone 3：多智能体 Orchestrator
- 实现 Agent 基类、WorkflowState、AgentTrace。
- 实现这些 agent：
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
- 一次资源生成至少产出 6 类资源：
  - 课程讲解文档
  - Mermaid 思维导图
  - 分层练习题
  - 拓展阅读材料
  - 视频/动画脚本
  - Python 代码实操案例
- 每个资源必须包含：
  - type
  - title
  - content_format
  - content
  - source_refs
  - difficulty
  - target_profile
  - review_status
  - created_by_agents
- 验收：资源生成任务能产生完整 Agent Trace。

Milestone 4：课程知识库
- 创建“人工智能导论”课程样例知识库。
- 至少 12 章，每章包含：
  - 学习目标
  - 核心概念
  - 重点难点
  - 常见误区
  - 示例讲解
  - 练习题草案
  - 拓展阅读建议
  - 实践任务建议
- 至少准备 60 道题目草案。
- 至少准备 3 个 Python 实操案例主题。
- 验收：后端生成资源时能引用课程知识库来源 ID。

Milestone 5：前端核心页面
- 实现页面：
  - /
  - /profile
  - /generate
  - /resources
  - /path
  - /tutor
  - /assessment
- 实现组件：
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
- 验收：前端可以通过后端 Mock API 跑通核心演示流程。

Milestone 6：学习路径、辅导与评估
- 实现学习路径接口和页面展示。
- 实现智能辅导 Mock 闭环。
- 实现练习提交、评估报告、画像弱点更新、路径调整。
- 验收：学生提交一次练习后，系统能展示评估报告并调整推荐。

Milestone 7：防幻觉、安全与体验
- 所有生成资源都展示来源、难度、审核状态。
- ReviewAgent 能标记 passed、needs_revision、blocked。
- 长任务必须有生成进度或轮询进度，避免白屏。
- Markdown、代码块、Mermaid 要能渲染；失败时显示 fallback。
- 验收：核心页面无明显白屏、空数据、接口错误。

Milestone 8：交付文档和演示材料
- 创建或完善：
  - docs/delivery/system-development-guide.md
  - docs/delivery/test-guide.md
  - docs/delivery/deployment-guide.md
  - docs/delivery/open-source-and-ai-tools.md
  - docs/delivery/ppt-outline.md
  - docs/delivery/demo-video-script.md
- PPT 大纲控制在 12 页以内。
- 视频脚本控制在 7 分钟以内。
- 开源组件和 AI Coding 工具说明必须单独列出。
- 涉及科大讯飞具体模型/API 时，不要凭空写死协议，标注“以官方文档为准”。

Milestone 9：最终联调与修复
- 运行后端测试。
- 运行前端 build。
- 手动或脚本验证完整流程：
  1. 进入学习工作台。
  2. 通过画像对话更新学生画像。
  3. 发起资源生成。
  4. 查看生成进度和 Agent Trace。
  5. 查看至少 6 类资源。
  6. 生成学习路径。
  7. 提交练习答案。
  8. 查看评估报告和路径调整。
- 修复阻断演示的问题。

执行方式：
- 每次修改前先快速查看现有文件结构。
- 优先小步修改，不做无关重构。
- 如果已有用户代码，不要随意删除或重写。
- 每完成一个里程碑，更新 README 或开发记录中的当前状态。
- 如果某个功能暂时只能 Mock，也要保证数据结构与真实实现兼容。
- 如果测试命令失败，先尝试修复；如果无法修复，说明具体原因和失败日志摘要。

最终回复必须使用以下格式：

完成内容：
- ...

修改文件：
- ...

验证命令：
- ...

验证结果：
- ...

可演示流程：
- ...

未完成 / 风险：
- ...

下一步建议：
- ...
```

## 更强硬的自主执行版本

如果你使用的 agent 经常只写计划、不动手，可以用下面这个版本开头替换上面提示词第一段：

```text
你不是咨询顾问，而是当前仓库的主开发 agent。请直接修改文件、运行命令、修复错误并持续推进，直到 MVP 闭环可运行。不要只输出计划；计划最多 8 行，然后立即开始实现。遇到普通技术问题请自行选择合理方案解决，只有涉及删除大量用户文件、真实付费服务、密钥泄露或不可逆操作时才暂停询问。
```

## 停止条件

只有出现以下情况才应该停下来问人：

- 需要真实 API Key 或账号权限。
- 需要删除大量已有文件。
- 需要选择付费云服务。
- 需求互相冲突，无法通过合理默认值解决。
- 构建工具或环境缺失，且无法自动安装或替代。

