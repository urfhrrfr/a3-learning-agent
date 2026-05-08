# Backend Agent Brief

## Mission

实现 Python FastAPI 后端骨架，为多智能体学习系统提供稳定 API、数据模型、任务进度和本地持久化。

## Read First

- `docs/project-blueprint.md`
- `docs/agent-execution-pack.md`

## Ownership

你负责后端基础设施，不负责 Vue 页面实现，不负责课程内容撰写。

建议目录：

```text
backend/
  app/
    main.py
    api/
    core/
    db/
    models/
    schemas/
    services/
    agents/
    providers/
    tests/
```

## Required Work

1. 建立 FastAPI 应用。
2. 实现配置读取：模型 Key、数据库路径、向量库路径、Mock 模式。
3. 实现数据库模型：
   - StudentProfile
   - ProfileVersion
   - Course
   - KnowledgeChunk
   - GenerationJob
   - AgentTrace
   - Resource
   - LearningPath
   - QuizAttempt
   - AssessmentReport
4. 实现 API：
   - `POST /api/profile/chat`
   - `GET /api/profile/current`
   - `POST /api/resources/generate`
   - `GET /api/jobs/{job_id}`
   - `GET /api/jobs/{job_id}/events`
   - `GET /api/resources`
   - `GET /api/resources/{resource_id}`
   - `POST /api/learning-path/generate`
   - `GET /api/learning-path/current`
   - `POST /api/tutor/chat`
   - `POST /api/quiz/submit`
   - `GET /api/assessment/report`
5. 提供 SSE 进度事件。
6. 提供 MockLLMProvider，未配置真实模型时也能运行。
7. 提供统一错误格式。

## API Response Rule

所有接口返回结构应可预测：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

错误：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数错误"
  }
}
```

## Acceptance Criteria

- 后端可独立启动。
- 没有真实 LLM Key 也能完成完整演示。
- API 文档可在 FastAPI Swagger 中查看。
- SSE 能持续返回 `job_started`、`agent_started`、`agent_completed`、`resource_ready`、`job_completed`。
- 至少有后端单元测试覆盖画像更新、资源生成任务创建、学习评估提交。

## Do Not Do

- 不要把前端代码放进后端。
- 不要在 API 层写大量 prompt 逻辑。
- 不要把所有数据塞进一个 JSON 文件。
- 不要强依赖真实模型 Key 才能演示。

