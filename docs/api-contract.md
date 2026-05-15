# API Contract

本文档是前端调用后端接口的契约说明。前端同学可按本文档完成页面联调；标注“待后端确认”的字段表示当前实现未强约束或后续可能扩展。

## 1. 通用约定

### 1.1 Base URL

- 开发环境前端默认使用相对路径调用：`/api/...`
- 如需配置后端地址，前端可通过 `VITE_API_BASE` 指定，例如：`http://localhost:8000`

### 1.2 Headers

```http
Content-Type: application/json
Accept: application/json
```

认证当前未启用。后续如接入登录态，建议统一增加：

```http
Authorization: Bearer <access_token>
```

### 1.3 统一成功返回结构

当前后端实际返回结构如下：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

字段说明：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| ok | boolean | 是 | 请求是否成功。成功为 `true` |
| data | object/array/null | 是 | 业务数据。不同接口结构不同 |
| error | object/null | 是 | 成功时为 `null` |

说明：需求中提到的 `{ "success": true, "data": {}, "message": "ok" }` 是可选统一风格建议；当前代码使用 `ok/data/error`，前端应以当前实现为准。

### 1.4 统一错误返回结构

业务错误统一返回：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "resource not found",
    "details": {}
  }
}
```

字段说明：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| ok | boolean | 是 | 请求是否成功。失败为 `false` |
| data | null | 是 | 失败时为 `null` |
| error.code | string | 是 | 业务错误码 |
| error.message | string | 是 | 可展示或记录的错误信息 |
| error.details | object | 否 | 调试详情或字段错误 |

### 1.5 错误码建议

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| BAD_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | 未登录或 token 无效，待后端确认 |
| FORBIDDEN | 403 | 无权限，待后端确认 |
| JOB_NOT_FOUND | 404 | 任务不存在 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 422 | 请求体校验失败 |
| INTERNAL_ERROR | 500 | 服务端异常 |

### 1.6 时间格式

所有时间字段建议使用 ISO 8601 字符串，例如：

```json
"2026-05-08T18:30:00Z"
```

当前返回字段包括：`updated_at`、`created_at`、`started_at`、`finished_at`、`completed_at`。

### 1.7 分页格式

当前资源列表接口未分页，直接返回数组。后续数据量增加时建议使用：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

### 1.8 异步任务状态

资源生成接口当前会同步完成并返回完整 `job`，但数据结构已包含任务状态，前端可按异步任务方式兼容。

| 状态 | 说明 |
| --- | --- |
| queued | 已入队，等待执行 |
| running | 执行中 |
| completed | 已完成 |
| failed | 执行失败 |

任务进度字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 任务 ID |
| status | string | 是 | `queued`、`running`、`completed`、`failed` |
| progress | number | 是 | 0-100 的进度 |
| current_step | string | 是 | 当前执行步骤或智能体名称 |
| traces | AgentTrace[] | 是 | 多智能体执行轨迹 |
| resources | Resource[] | 是 | 已生成资源 |
| events | object[] | 是 | 任务事件流记录 |
| created_at | string | 是 | 创建时间 |
| completed_at | string/null | 否 | 完成时间 |

## 2. 数据模型

### 2.1 Profile

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 学习者画像 ID |
| major | string | 是 | 专业 |
| education_level | string | 是 | 学段或年级 |
| course | string | 是 | 当前课程 |
| current_chapter | string | 是 | 当前章节 |
| knowledge_base | string[] | 是 | 已有知识基础 |
| learning_goal | string | 是 | 学习目标 |
| cognitive_style | string | 是 | 认知或学习偏好 |
| preferred_modalities | string[] | 是 | 偏好的资源形式 |
| time_budget | string | 是 | 学习时间预算 |
| weak_points | string[] | 是 | 薄弱点 |
| mistake_patterns | string[] | 是 | 常见错误模式 |
| interests | string[] | 是 | 兴趣方向 |
| mastery | number | 是 | 掌握度，范围建议为 0-1 |
| version | number | 是 | 画像版本号 |
| updated_at | string | 是 | 更新时间 |

### 2.2 Resource

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 资源 ID |
| type | string | 是 | 资源类型，如讲解、练习、代码案例等 |
| title | string | 是 | 资源标题 |
| content_format | string | 是 | `markdown`、`mermaid`、`json`、`code` |
| content | string | 是 | 资源正文 |
| source_refs | string[] | 是 | 来源引用 |
| difficulty | string | 是 | 难度 |
| target_profile | string[] | 是 | 面向的画像特征 |
| review_status | string | 是 | `passed`、`needs_revision`、`blocked` |
| created_by_agents | string[] | 是 | 参与生成的智能体 |
| created_at | string | 是 | 创建时间 |

### 2.3 AgentTrace

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | Trace ID |
| job_id | string | 是 | 所属任务 ID |
| agent | string | 是 | 智能体名称 |
| status | string | 是 | `pending`、`running`、`completed`、`failed` |
| input_summary | string | 是 | 输入摘要 |
| output_summary | string | 是 | 输出摘要 |
| source_refs | string[] | 是 | 来源引用 |
| warnings | string[] | 是 | 风险或警告 |
| confidence | number | 是 | 置信度，范围建议为 0-1 |
| started_at | string | 是 | 开始时间 |
| finished_at | string/null | 否 | 结束时间 |

### 2.4 LearningPath

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 学习路径 ID |
| profile_version | number | 是 | 生成路径时对应的画像版本 |
| mastery | number | 是 | 当前掌握度 |
| steps | LearningPathStep[] | 是 | 路径步骤 |
| adjustment_reason | string | 是 | 路径生成或调整原因 |
| updated_at | string | 是 | 更新时间 |

### 2.5 LearningPathStep

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 步骤 ID |
| title | string | 是 | 步骤标题 |
| objective | string | 是 | 学习目标 |
| recommended_resource_ids | string[] | 是 | 推荐资源 ID 列表 |
| reason | string | 是 | 推荐原因 |
| estimated_minutes | number | 是 | 预计学习分钟数 |
| status | string | 是 | `todo`、`doing`、`done` |

### 2.6 AssessmentReport

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 测评报告 ID |
| score | number | 是 | 分数 |
| mastery_delta | number | 是 | 掌握度变化 |
| strengths | string[] | 是 | 优势点 |
| weak_points | string[] | 是 | 薄弱点 |
| mistake_patterns | string[] | 是 | 错误模式 |
| feedback | string | 是 | 学习反馈 |
| adjusted_path | LearningPath | 是 | 根据测评调整后的学习路径 |
| created_at | string | 是 | 创建时间 |

## 3. 接口列表

### 3.1 GET /api/health

#### 用途

健康检查接口。前端可在应用启动、开发联调或部署验收时调用，用于判断后端服务是否可用。

#### 请求示例

```http
GET /api/health
Accept: application/json
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "status": "healthy",
    "mock_llm": true,
    "llm_provider": "mock",
    "cache": {
      "enabled": false,
      "available": false,
      "reason": "REDIS_URL not configured"
    },
    "course": "人工智能导论"
  },
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| status | string | 是 | 服务状态，正常为 `healthy` |
| mock_llm | boolean | 是 | 是否使用 mock LLM |
| llm_provider | string | 是 | 当前 LLM Provider 名称 |
| cache | object | 是 | Redis 可选缓存状态；未配置时 `enabled=false`，系统仍使用 SQLite 正常运行 |
| course | string | 是 | 当前课程名称 |

#### 前端使用页面

- 健康检查页或调试面板，待前端确认
- 应用启动连通性检测，待前端确认

### 3.2 POST /api/profile/chat

#### 用途

画像对话接口。前端在用户画像页提交学生自述、偏好、目标或薄弱点时调用，后端会从消息中抽取信息并更新学习画像。

#### 请求示例

```http
POST /api/profile/chat
Content-Type: application/json
Accept: application/json
```

```json
{
  "message": "我线性代数比较薄弱，希望多给 Python 代码案例"
}
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "profile": {
      "id": "student_demo",
      "major": "计算机科学与技术",
      "education_level": "本科二年级",
      "course": "人工智能导论",
      "current_chapter": "机器学习基础",
      "knowledge_base": ["Python 基础", "线性代数薄弱"],
      "learning_goal": "理解机器学习核心概念并完成课程项目",
      "cognitive_style": "例子驱动",
      "preferred_modalities": ["图解", "代码案例", "短视频"],
      "time_budget": "每天 45 分钟",
      "weak_points": ["梯度下降", "模型评估指标"],
      "mistake_patterns": ["概念混淆", "公式不会迁移"],
      "interests": ["智能教育", "机器学习应用"],
      "mastery": 0.42,
      "version": 2,
      "updated_at": "2026-05-08T18:30:00Z"
    },
    "extracted": {
      "weak_math": true,
      "preferred_modality": "代码案例"
    },
    "suggested_next_question": "你希望下一份资源更偏图解、代码实操，还是练习巩固？",
    "version_change": "画像已更新到 v2"
  },
  "error": null
}
```

#### 字段说明

请求字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| message | string | 是 | 用户输入的画像补充信息 |

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| profile | Profile | 是 | 更新后的学习画像 |
| extracted | object | 是 | 本轮对话抽取出的结构化信息 |
| suggested_next_question | string | 是 | 建议前端继续追问的问题 |
| version_change | string | 是 | 画像版本变化说明 |

#### 前端使用页面

- 用户画像页 `Profile.vue`
- 画像洞察面板 `ProfileInsightPanel.vue`
- 画像采集聊天组件 `ChatPanel.vue`

### 3.3 GET /api/profile/current

#### 用途

获取当前学习画像。前端在页面初始化、资源生成前、测评提交后刷新画像时调用。

#### 请求示例

```http
GET /api/profile/current
Accept: application/json
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "student_demo",
    "major": "计算机科学与技术",
    "education_level": "本科二年级",
    "course": "人工智能导论",
    "current_chapter": "机器学习基础",
    "knowledge_base": ["Python 基础", "线性代数薄弱"],
    "learning_goal": "理解机器学习核心概念并完成课程项目",
    "cognitive_style": "例子驱动",
    "preferred_modalities": ["图解", "代码案例", "短视频"],
    "time_budget": "每天 45 分钟",
    "weak_points": ["梯度下降", "模型评估指标"],
    "mistake_patterns": ["概念混淆", "公式不会迁移"],
    "interests": ["智能教育", "机器学习应用"],
    "mastery": 0.42,
    "version": 2,
    "updated_at": "2026-05-08T18:30:00Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：见 `2.1 Profile`。

#### 前端使用页面

- 用户画像页
- 资源生成页
- 学习路径页
- 测评报告页
- 全局 Store 初始化 `store.refresh()`

### 3.4 POST /api/resources/generate

#### 用途

生成个性化学习资源。前端在资源生成页点击“启动生成”时调用，后端根据课程、章节、学习目标和薄弱点生成资源、智能体 Trace 和学习路径。

#### 请求示例

```http
POST /api/resources/generate
Content-Type: application/json
Accept: application/json
```

```json
{
  "course": "人工智能导论",
  "chapter": "机器学习基础",
  "goal": "理解泛化与过拟合，并完成练习",
  "pain_points": ["公式迁移", "模型评估指标"]
}
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "job_12ab34cd",
    "status": "completed",
    "progress": 100,
    "current_step": "job_completed",
    "request": {
      "course": "人工智能导论",
      "chapter": "机器学习基础",
      "goal": "理解泛化与过拟合，并完成练习",
      "pain_points": ["公式迁移", "模型评估指标"]
    },
    "traces": [
      {
        "id": "trace_001",
        "job_id": "job_12ab34cd",
        "agent": "KnowledgeAgent",
        "status": "completed",
        "input_summary": "检索课程章节知识点",
        "output_summary": "找到机器学习基础相关片段",
        "source_refs": ["ai_intro/ch04#concepts"],
        "warnings": [],
        "confidence": 0.86,
        "started_at": "2026-05-08T18:30:00Z",
        "finished_at": "2026-05-08T18:30:03Z"
      }
    ],
    "resources": [
      {
        "id": "res_001",
        "type": "concept_explanation",
        "title": "泛化与过拟合图解",
        "content_format": "markdown",
        "content": "## 泛化是什么\n...",
        "source_refs": ["ai_intro/ch04#concepts"],
        "difficulty": "basic",
        "target_profile": ["例子驱动", "图解"],
        "review_status": "passed",
        "created_by_agents": ["KnowledgeAgent", "ResourceAgent"],
        "created_at": "2026-05-08T18:30:05Z"
      }
    ],
    "events": [
      {
        "type": "job_started",
        "payload": {
          "job_id": "job_12ab34cd"
        },
        "created_at": "2026-05-08T18:30:00Z"
      }
    ],
    "created_at": "2026-05-08T18:30:00Z",
    "completed_at": "2026-05-08T18:30:10Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| course | string | 否 | 课程名称。不传时后端使用默认课程 |
| chapter | string | 否 | 章节名称。不传时后端使用默认章节 |
| goal | string | 否 | 生成目标。不传时后端使用默认目标 |
| pain_points | string[] | 否 | 用户薄弱点列表 |

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| id | string | 是 | 生成任务 ID |
| status | string | 是 | 任务状态 |
| progress | number | 是 | 任务进度，0-100 |
| current_step | string | 是 | 当前步骤 |
| request | object | 是 | 本次生成请求参数 |
| traces | AgentTrace[] | 是 | 多智能体执行轨迹 |
| resources | Resource[] | 是 | 生成出的资源 |
| events | object[] | 是 | 任务事件记录 |
| created_at | string | 是 | 创建时间 |
| completed_at | string/null | 否 | 完成时间 |

#### 前端使用页面

- 资源生成页 `Generate.vue`
- 生成进度组件 `GenerationProgress.vue`
- 智能体轨迹组件 `AgentTraceTimeline.vue`
- 资源卡片组件 `ResourceCard.vue`

### 3.5 GET /api/jobs/{job_id}

#### 用途

查询资源生成任务详情。前端可用于异步轮询任务状态、刷新进度、恢复生成结果。当前前端暂未封装此接口，待前端确认是否接入。

#### 请求示例

```http
GET /api/jobs/job_12ab34cd
Accept: application/json
```

Path Params：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| job_id | string | 是 | 资源生成任务 ID |

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "job_12ab34cd",
    "status": "running",
    "progress": 56,
    "current_step": "ResourceAgent",
    "request": {
      "course": "人工智能导论",
      "chapter": "机器学习基础",
      "goal": "理解泛化与过拟合，并完成练习",
      "pain_points": ["模型评估指标"]
    },
    "traces": [],
    "resources": [],
    "events": [],
    "created_at": "2026-05-08T18:30:00Z",
    "completed_at": null
  },
  "error": null
}
```

#### 字段说明

请求字段：见 Path Params。

返回字段：见 `1.8 异步任务状态`。

#### 前端使用页面

- 资源生成页
- 生成进度组件
- 任务恢复或轮询逻辑，待前端确认

### 3.6 GET /api/resources

#### 用途

获取资源列表。前端在资源库页、资源生成页、学习路径推荐资源映射时调用。

#### 请求示例

```http
GET /api/resources
Accept: application/json
```

Query Params：当前无。后续可扩展 `type`、`difficulty`、`page`、`page_size`，待后端确认。

#### 返回示例

```json
{
  "ok": true,
  "data": [
    {
      "id": "res_001",
      "type": "concept_explanation",
      "title": "泛化与过拟合图解",
      "content_format": "markdown",
      "content": "## 泛化是什么\n...",
      "source_refs": ["ai_intro/ch04#concepts"],
      "difficulty": "basic",
      "target_profile": ["例子驱动", "图解"],
      "review_status": "passed",
      "created_by_agents": ["KnowledgeAgent", "ResourceAgent"],
      "created_at": "2026-05-08T18:30:05Z"
    }
  ],
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| data | Resource[] | 是 | 资源数组，资源字段见 `2.2 Resource` |

#### 前端使用页面

- 资源库页 `Resources.vue`
- 资源生成页 `Generate.vue`
- 学习路径页资源跳转，待前端确认
- 全局 Store 初始化 `store.refresh()`

### 3.7 GET /api/resources/{resource_id}

#### 用途

获取单个资源详情。前端可在资源详情页、资源弹窗、学习路径点击推荐资源时调用。当前前端主要直接使用资源列表中的完整资源对象，单独详情页待前端确认。

#### 请求示例

```http
GET /api/resources/res_001
Accept: application/json
```

Path Params：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| resource_id | string | 是 | 资源 ID |

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "res_001",
    "type": "concept_explanation",
    "title": "泛化与过拟合图解",
    "content_format": "markdown",
    "content": "## 泛化是什么\n...",
    "source_refs": ["ai_intro/ch04#concepts"],
    "difficulty": "basic",
    "target_profile": ["例子驱动", "图解"],
    "review_status": "passed",
    "created_by_agents": ["KnowledgeAgent", "ResourceAgent"],
    "created_at": "2026-05-08T18:30:05Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：见 Path Params。

返回字段：见 `2.2 Resource`。

#### 前端使用页面

- 资源详情页，待前端确认
- 资源库页详情区域 `Resources.vue`
- 学习路径推荐资源点击查看，待前端确认

### 3.8 POST /api/learning-path/generate

#### 用途

重新生成学习路径。前端可在用户主动刷新路径、画像更新后、资源生成后调用。当前后端不需要请求体，会基于当前画像和资源生成路径。

#### 请求示例

```http
POST /api/learning-path/generate
Content-Type: application/json
Accept: application/json
```

Body JSON：当前无需传参。

```json
{}
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "path_12ab34cd",
    "profile_version": 2,
    "mastery": 0.42,
    "steps": [
      {
        "id": "step_01",
        "title": "概念热身",
        "objective": "建立章节框架，识别易混概念",
        "recommended_resource_ids": ["res_001", "res_002"],
        "reason": "画像显示偏好图解和例子驱动，先用讲解与导图降低门槛。",
        "estimated_minutes": 20,
        "status": "doing"
      }
    ],
    "adjustment_reason": "基于当前画像生成路径",
    "updated_at": "2026-05-08T18:30:00Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：见 `2.4 LearningPath` 和 `2.5 LearningPathStep`。

#### 前端使用页面

- 学习路径页 `Path.vue`
- 测评报告页路径刷新，待前端确认
- 资源生成完成后的路径更新逻辑

### 3.9 GET /api/learning-path/current

#### 用途

获取当前学习路径。前端在页面初始化、资源生成后、测评提交后刷新路径时调用。如果当前没有路径，后端会自动生成一条演示路径。

#### 请求示例

```http
GET /api/learning-path/current
Accept: application/json
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "path_12ab34cd",
    "profile_version": 2,
    "mastery": 0.42,
    "steps": [
      {
        "id": "step_01",
        "title": "概念热身",
        "objective": "建立章节框架，识别易混概念",
        "recommended_resource_ids": ["res_001", "res_002"],
        "reason": "画像显示偏好图解和例子驱动，先用讲解与导图降低门槛。",
        "estimated_minutes": 20,
        "status": "doing"
      }
    ],
    "adjustment_reason": "初始化演示学习路径",
    "updated_at": "2026-05-08T18:30:00Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：见 `2.4 LearningPath` 和 `2.5 LearningPathStep`。

#### 前端使用页面

- 学习路径页 `Path.vue`
- 测评报告页 `Assessment.vue`
- 全局 Store 初始化 `store.refresh()`

### 3.10 POST /api/tutor/chat

#### 用途

AI 导师问答接口。前端在智能辅导页提交学生问题时调用，可选绑定某个资源 ID，让回答更贴合当前学习材料。

#### 请求示例

```http
POST /api/tutor/chat
Content-Type: application/json
Accept: application/json
```

```json
{
  "question": "为什么训练准确率高，测试效果仍然可能不好？",
  "resource_id": "res_001"
}
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "answer": "可以把当前问题拆成“概念定义、适用条件、反例”三步...",
    "source_refs": ["ai_intro/ch04#concepts"],
    "mermaid": "flowchart LR\nA[训练数据] --> B[模型]\nB --> C[预测]\nC --> D[评价指标]"
  },
  "error": null
}
```

#### 字段说明

请求字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| question | string | 是 | 学生问题 |
| resource_id | string/null | 否 | 关联资源 ID。不传则基于当前课程和画像回答 |

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| answer | string | 是 | 导师回答，前端可按 Markdown 渲染 |
| source_refs | string[] | 是 | 回答引用来源 |
| mermaid | string | 是 | 可选 Mermaid 图。当前实现总是返回字符串，可能为空待后端确认 |

#### 前端使用页面

- AI 导师聊天页 `Tutor.vue`
- Markdown 渲染组件 `MarkdownRenderer.vue`
- Mermaid 渲染组件 `MermaidRenderer.vue`

### 3.11 POST /api/quiz/submit

#### 用途

提交测验答案并生成测评报告。前端在测验页用户提交答案后调用，后端会计算分数、更新画像掌握度，并返回调整后的学习路径。

#### 请求示例

```http
POST /api/quiz/submit
Content-Type: application/json
Accept: application/json
```

```json
{
  "answers": [
    "过拟合会导致泛化下降",
    "测试集用于评估模型在新样本上的表现"
  ],
  "resource_id": "res_quiz_001"
}
```

#### 返回示例

```json
{
  "ok": true,
  "data": {
    "id": "assess_12ab34cd",
    "score": 86,
    "mastery_delta": 0.12,
    "strengths": ["能识别训练/测试拆分", "能用例子解释模型评估"],
    "weak_points": ["模型评估指标"],
    "mistake_patterns": ["少量术语表达不严谨"],
    "feedback": "建议下一轮先复习评价指标，再完成代码案例中的预测解释任务。",
    "adjusted_path": {
      "id": "path_12ab34cd",
      "profile_version": 3,
      "mastery": 0.54,
      "steps": [
        {
          "id": "step_01",
          "title": "概念热身",
          "objective": "建立章节框架，识别易混概念",
          "recommended_resource_ids": ["res_001"],
          "reason": "根据练习提交结果加强评价指标与迁移练习。",
          "estimated_minutes": 20,
          "status": "doing"
        }
      ],
      "adjustment_reason": "根据练习提交结果调整",
      "updated_at": "2026-05-08T18:30:00Z"
    },
    "created_at": "2026-05-08T18:30:00Z"
  },
  "error": null
}
```

#### 字段说明

请求字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| answers | string[] | 是 | 用户提交的答案列表 |
| resource_id | string/null | 否 | 所属测验或资源 ID |

返回字段：见 `2.6 AssessmentReport`。

#### 前端使用页面

- 测验页 `Assessment.vue`
- 测验组件 `QuizPlayer.vue`
- 测评报告组件 `AssessmentReport.vue`
- 学习路径组件 `LearningPathTimeline.vue`

### 3.12 GET /api/assessment/report

#### 用途

获取最近一次测评报告。前端在测评报告页初始化或刷新时调用。若尚未提交测验，当前后端返回 `data: null`。

#### 请求示例

```http
GET /api/assessment/report
Accept: application/json
```

#### 返回示例

有报告时：

```json
{
  "ok": true,
  "data": {
    "id": "assess_12ab34cd",
    "score": 86,
    "mastery_delta": 0.12,
    "strengths": ["能识别训练/测试拆分", "能用例子解释模型评估"],
    "weak_points": ["模型评估指标"],
    "mistake_patterns": ["少量术语表达不严谨"],
    "feedback": "建议下一轮先复习评价指标，再完成代码案例中的预测解释任务。",
    "adjusted_path": {
      "id": "path_12ab34cd",
      "profile_version": 3,
      "mastery": 0.54,
      "steps": [],
      "adjustment_reason": "根据练习提交结果调整",
      "updated_at": "2026-05-08T18:30:00Z"
    },
    "created_at": "2026-05-08T18:30:00Z"
  },
  "error": null
}
```

无报告时：

```json
{
  "ok": true,
  "data": null,
  "error": null
}
```

#### 字段说明

请求字段：无。

返回字段：

| 字段名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| data | AssessmentReport/null | 是 | 最近一次测评报告；未提交测验时为 `null` |

#### 前端使用页面

- 测评报告页 `Assessment.vue`
- 测评报告组件 `AssessmentReport.vue`
- 全局 Store 初始化 `store.refresh()`

## 4. 前端接入建议

### 4.1 调用顺序建议

应用启动或页面刷新：

1. `GET /api/profile/current`
2. `GET /api/resources`
3. `GET /api/learning-path/current`
4. `GET /api/assessment/report`

资源生成：

1. `POST /api/resources/generate`
2. 使用返回的 `resources` 和 `traces` 更新页面
3. `GET /api/learning-path/current` 刷新学习路径

测验提交：

1. `POST /api/quiz/submit`
2. 使用返回的 `adjusted_path` 更新路径
3. `GET /api/profile/current` 刷新画像掌握度

### 4.2 前端类型建议

前端可直接对齐 `frontend/src/types.ts` 中的类型定义：

- `Profile`
- `AgentTrace`
- `Resource`
- `LearningPath`
- `AssessmentReport`

缺少但建议补充的类型：

- `GenerationJob`
- `ApiResponse<T>`
- `TutorResponse`
- `ProfileChatResponse`
