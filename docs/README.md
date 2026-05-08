# A3 Personalized Learning Multi-Agent System Docs

本目录是比赛项目的启动执行包，面向 Python 后端 + Vue 前端的实现路线。

建议阅读顺序：

1. `project-blueprint.md`：项目定位、MVP 范围、架构、风险和评分映射。
2. `agent-execution-pack.md`：可直接交给其他 agent 的总任务书。
3. `agent-prompt-guide.md`：Cursor / Trae / Claude Code 的分工投喂方式。
4. `one-shot-autonomous-agent-prompt.md`：一次性粘贴给主 agent 的自主开发提示词。
5. `agent-briefs/*.md`：按职责拆分的专项 agent 任务。

推荐先做 MVP，不要一开始追求完整商业化平台。MVP 的核心目标是：

- 能通过对话构建不少于 6 个维度的学生画像。
- 能体现清晰、可观察的多智能体协作流程。
- 能生成至少 5 类个性化资源。
- 能形成动态学习路径和资源推送。
- 能展示防幻觉、内容安全、流式输出或进度追踪。
- 能支撑 7 分钟内的演示视频和答辩讲解。
