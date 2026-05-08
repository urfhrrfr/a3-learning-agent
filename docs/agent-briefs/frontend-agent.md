# Frontend Agent Brief

## Mission

实现 Vue 3 前端，让评委能清楚看到学习画像、多智能体协作、资源生成、学习路径和评估闭环。

## Read First

- `docs/project-blueprint.md`
- `docs/agent-execution-pack.md`

## Ownership

你负责前端页面、组件、状态管理和 API 对接。不负责后端算法实现。

## Required Pages

### 1. Learning Workspace

路径：`/`

作用：

- 展示当前学生画像摘要
- 展示当前学习路径
- 展示最近生成资源
- 展示继续学习入口

### 2. Profile Chat

路径：`/profile`

作用：

- 对话式构建画像
- 展示画像维度
- 展示画像版本变化

必须突出：

- 不是表单
- 画像会随对话更新
- 至少 6 个维度可见

### 3. Resource Generation

路径：`/generate`

作用：

- 输入课程、章节、学习目标和困惑
- 发起资源生成
- 展示 SSE 进度
- 展示 Agent Trace
- 资源生成完成后跳转资源库

### 4. Resources

路径：`/resources`

作用：

- 卡片化展示文档、思维导图、题库、阅读、视频脚本、代码案例
- 支持按资源类型过滤
- 资源详情支持 Markdown 和 Mermaid 渲染

### 5. Learning Path

路径：`/path`

作用：

- 用时间线展示个性化路径
- 每一步关联资源
- 展示推荐理由
- 展示掌握度变化

### 6. Tutor

路径：`/tutor`

作用：

- 结合当前资源和画像答疑
- 支持 Markdown、代码块、Mermaid 图解

### 7. Assessment

路径：`/assessment`

作用：

- 展示练习题
- 提交答案
- 展示评估报告
- 展示路径调整结果

## Required Components

- `ChatPanel`
- `ProfileInsightPanel`
- `ProfileVersionTimeline`
- `AgentTraceTimeline`
- `GenerationProgress`
- `ResourceCard`
- `MarkdownRenderer`
- `MermaidRenderer`
- `LearningPathTimeline`
- `QuizPlayer`
- `AssessmentReport`
- `TutorChat`

## UX Requirements

- 流式输出或进度追踪必须明显。
- 页面不要长时间白屏。
- 资源卡片要标注类型、难度、来源、审核状态。
- Agent Trace 要让评委看懂“多个智能体在协作”。
- Markdown 和代码块必须可读。
- Mermaid 图渲染失败时要显示原始文本 fallback。

## Acceptance Criteria

- 前端能连接后端 Mock 模式完成完整演示。
- 生成资源时能实时显示进度。
- 至少能展示 6 类资源。
- 至少能展示 10 个画像字段。
- npm build 通过。
- 移动端不需要完整适配，但桌面浏览器不能明显错位。

## Do Not Do

- 不要做营销落地页作为第一屏。
- 不要把核心功能藏在多层菜单里。
- 不要用纯聊天界面代替全部功能。
- 不要只展示静态 mock 而没有 API 对接。

