# Agent Execution Pack

这份文档用于交给其他 agent 执行项目任务。执行者应先阅读 `docs/project-blueprint.md`，再按自己的职责读取 `docs/agent-briefs/` 下的专项任务。

## 1. 项目目标

构建一个可运行的 Python + Vue 多智能体学习系统，用于参加“基于大模型的个性化资源生成与学习多智能体系统开发”赛题。

必须完成的演示闭环：

```text
学生对话输入学习情况
-> 系统抽取并更新学习画像
-> 多智能体协同生成个性化资源
-> 系统规划学习路径并推送资源
-> 学生完成练习
-> 系统评估学习效果并调整画像和路径
```

## 2. 技术决策

默认技术栈：

- 后端：Python 3.11+、FastAPI、Pydantic、SQLite、Chroma 或 FAISS
- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router、Element Plus 或 Naive UI
- 协议：REST + SSE
- 大模型：通过 Provider 接口接入，优先预留科大讯飞相关模型配置；模型名称、鉴权和协议以官方文档为准
- 多智能体：自研轻量 Orchestrator，所有 Agent 都要有结构化输入输出和 trace

## 3. MVP 功能范围

必须实现：

- 对话式学习画像构建
- 画像不少于 6 个维度，建议 10 个
- 一门课程知识库：人工智能导论
- 多智能体资源生成
- 至少 5 类资源，建议 6 类
- 个性化学习路径
- 资源推送
- 生成进度追踪或流式输出
- 防幻觉与内容安全机制
- 测试说明和演示材料

建议实现的加分项：

- 智能辅导
- 学习效果评估
- 错题反馈后动态调整路径

暂不做：

- 复杂权限系统
- 真实支付、班级管理、教师端复杂后台
- 大规模并发
- 移动端原生 App
- 完整视频生成平台

## 4. 推荐任务拆分

### Agent A：Backend Agent

读取：`docs/agent-briefs/backend-agent.md`

负责：

- FastAPI 项目结构
- 数据模型
- API 路由
- SSE 任务进度
- 本地持久化
- Provider 抽象接口

### Agent B：Multi-Agent Orchestrator Agent

读取：`docs/agent-briefs/orchestrator-agent.md`

负责：

- Agent 基类
- WorkflowState
- ProfileAgent、KnowledgeAgent、PlannerAgent、资源生成 Agent、ReviewAgent
- Agent Trace
- 资源生成流水线

### Agent C：Frontend Agent

读取：`docs/agent-briefs/frontend-agent.md`

负责：

- Vue 页面
- 画像对话 UI
- Agent Trace UI
- 资源卡片
- 学习路径时间线
- 练习与评估 UI

### Agent D：Knowledge Base Agent

读取：`docs/agent-briefs/knowledge-agent.md`

负责：

- 人工智能导论课程知识库
- 章节文档
- 示例题目
- 常见误区
- 代码实验主题
- 导入格式

### Agent E：QA, Docs and Demo Agent

读取：`docs/agent-briefs/qa-docs-demo-agent.md`

负责：

- 测试策略
- 测试说明书
- 系统开发说明书大纲
- PPT 大纲
- 7 分钟演示视频脚本
- 开源协议和 AI Coding 工具说明

## 5. 全局协作规则

所有 agent 必须遵守：

- 不改变既定 MVP 范围，除非发现硬性阻塞。
- 优先保证可运行闭环，再优化体验。
- 所有大模型输出都要结构化保存，便于前端渲染。
- 所有生成资源都要带 `source_refs`、`difficulty`、`target_profile`、`review_status`。
- 不要把多智能体做成隐藏黑盒，必须产生可展示 trace。
- 没有真实模型 Key 时，必须提供 MockLLMProvider，保证系统可演示。
- 不要引入没有必要的新依赖。
- 代码、文档、演示都要能支撑评委看到赛题要求。

## 6. 关键接口契约

画像对象：

```json
{
  "major": "计算机科学与技术",
  "education_level": "本科二年级",
  "course": "人工智能导论",
  "knowledge_base": ["Python基础", "线性代数薄弱"],
  "learning_goal": "理解机器学习并完成课程项目",
  "cognitive_style": "例子驱动",
  "preferred_modalities": ["图解", "代码案例", "短视频"],
  "time_budget": "每天45分钟",
  "weak_points": ["梯度下降", "模型评估指标"],
  "mistake_patterns": ["概念混淆", "公式不会迁移"],
  "progress": {
    "current_chapter": "机器学习基础",
    "mastery": 0.42
  }
}
```

资源对象：

```json
{
  "id": "res_001",
  "type": "lecture_doc",
  "title": "面向例子驱动学习者的机器学习基础讲解",
  "content_format": "markdown",
  "content": "...",
  "source_refs": ["ai_intro/ch04#chunk-03"],
  "difficulty": "入门",
  "target_profile": ["例子驱动", "线性代数薄弱"],
  "review_status": "passed",
  "created_by_agents": ["KnowledgeAgent", "LectureAgent", "ReviewAgent"]
}
```

Agent Trace 对象：

```json
{
  "job_id": "job_001",
  "agent": "QuizAgent",
  "status": "completed",
  "input_summary": "为线性代数薄弱的本科生生成机器学习入门练习",
  "output_summary": "生成 8 道分层题目，包含答案和解析",
  "started_at": "2026-04-28T20:00:00+08:00",
  "finished_at": "2026-04-28T20:00:08+08:00"
}
```

## 7. 里程碑

### Milestone 1：项目骨架

完成标准：

- 前后端能启动
- Mock 数据可展示
- 基础路由和页面存在

### Milestone 2：画像与知识库

完成标准：

- 画像对话可更新 profile
- 初始课程知识库可检索
- 前端可展示画像版本

### Milestone 3：多智能体资源生成

完成标准：

- 一次请求能生成至少 5 类资源
- 可看到 Agent Trace
- 生成进度可见

### Milestone 4：学习路径与评估

完成标准：

- 根据画像生成学习路径
- 提交练习后生成评估报告
- 路径可根据结果调整

### Milestone 5：比赛交付材料

完成标准：

- README
- 系统开发说明书
- 测试说明书
- PPT 大纲
- 演示视频脚本
- 开源协议和 AI 工具说明

## 8. 最终验收命令建议

实际命令由代码仓库决定，但需要保留类似能力：

```bash
# backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
npm install
npm run dev

# tests
pytest
npm run build
```

