# A3 Personalized Learning Multi-Agent System Docs

本目录是比赛项目的启动执行包，面向 Python 后端 + Vue 前端的实现路线。

建议阅读顺序：

1. `project-blueprint.md`：项目定位、MVP 范围、架构、风险和评分映射。
2. `agent-execution-pack.md`：可直接交给其他 agent 的总任务书。
3. `agent-prompt-guide.md`：Cursor / Trae / Claude Code 的分工投喂方式。
4. `one-shot-autonomous-agent-prompt.md`：一次性粘贴给主 agent 的自主开发提示词。
5. `agent-briefs/*.md`：按职责拆分的专项 agent 任务。
6. `api-contract.md`：前后端接口契约，覆盖核心 `/api` 接口的请求、返回和页面使用说明。
7. `llm-provider.md`：真实大模型 Provider 接入说明，覆盖 Mock、科大讯飞星火和 OpenAI 兼容模型。
8. `seedance-video-integration-plan.md`：SeeDance 多模态视频生成的后端、前端和兜底接入方案。
9. `profile-dimensions-and-update-strategy.md`：画像维度定义、更新规则和版本轨迹说明。
10. `agent-collaboration-trace-evidence.md`：多智能体协同链路、冲突仲裁与真实 Trace 证据。
11. `delivery/demo-runbook.md`：答辩、录屏和现场展示时照着走的演示顺序。
12. `delivery/final-checklist.md`：提交前最终验收清单和演示流程。
13. `delivery/demo-video-script.md`：7 分钟演示视频脚本。
14. `delivery/ppt-outline.md`：12 页以内 PPT 大纲。
15. `delivery/presentation-and-defense-guide.md`：答辩话术、项目亮点和常见问答。
16. `delivery/submission-summary.md`：本轮完成内容、验证结果和建议提交信息。

推荐先做 MVP，不要一开始追求完整商业化平台。MVP 的核心目标是：

- 能通过对话构建不少于 6 个维度的学生画像。
- 能体现清晰、可观察的多智能体协作流程。
- 能生成至少 5 类个性化资源。
- 能形成动态学习路径和资源推送。
- 能展示防幻觉、内容安全、流式输出或进度追踪。
- 能支撑 7 分钟内的演示视频和答辩讲解。
