# Multi-Agent Orchestrator Agent Brief

## Mission

实现可展示、可测试的多智能体协同机制。重点不是堆 agent 名称，而是让每个 agent 有清晰职责、输入输出、trace 和审核闭环。

## Read First

- `docs/project-blueprint.md`
- `docs/agent-execution-pack.md`

## Ownership

你负责：

- Agent 抽象
- WorkflowState
- 多智能体资源生成流程
- Agent Trace
- 防幻觉审核逻辑

你不负责：

- Vue 页面
- 课程知识库正文
- 数据库底层封装

## Required Agents

必须实现：

- `ProfileAgent`
- `KnowledgeAgent`
- `PlannerAgent`
- `LectureAgent`
- `MindMapAgent`
- `QuizAgent`
- `ReadingAgent`
- `MediaAgent`
- `CodeCaseAgent`
- `ReviewAgent`
- `AssessmentAgent`

## Workflow

画像对话流程：

```text
UserMessage
-> ProfileAgent
-> ProfileVersion
-> SuggestedNextQuestion or CompletedProfile
```

资源生成流程：

```text
GenerationRequest
-> KnowledgeAgent 检索课程知识
-> PlannerAgent 决定资源组合
-> LectureAgent / MindMapAgent / QuizAgent / ReadingAgent / MediaAgent / CodeCaseAgent
-> ReviewAgent 审核事实、难度、来源和安全性
-> ResourceBundle
```

学习评估流程：

```text
QuizAttempt
-> AssessmentAgent
-> mastery report
-> updated weak_points and mistake_patterns
-> adjusted LearningPath
```

## Data Contracts

每个 Agent 输出必须包含：

```json
{
  "agent": "LectureAgent",
  "status": "completed",
  "result": {},
  "source_refs": [],
  "warnings": [],
  "confidence": 0.86
}
```

每个资源必须包含：

- type
- title
- content_format
- content
- source_refs
- difficulty
- target_profile
- review_status
- created_by_agents

## Anti-Hallucination Rules

ReviewAgent 至少检查：

- 是否引用了课程知识库来源。
- 是否出现没有来源支撑的具体事实。
- 是否难度符合用户画像。
- 是否包含敏感、违法、歧视或不适合高校课堂的内容。
- 是否有“模型不确定”的地方需要标注。

无法确认的内容不要硬编，应输出：

```text
该内容需要教师或资料进一步确认。
```

## Acceptance Criteria

- 任一生成任务能产生完整 Agent Trace。
- 至少 6 类资源可以由不同 Agent 生成。
- 资源生成失败时，单个资源失败不影响其他资源返回。
- ReviewAgent 能把不合格资源标记为 `needs_revision` 或 `blocked`。
- Mock 模式下也能返回结构完整的示例内容。

