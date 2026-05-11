# 提交说明

本文档汇总本轮从接口契约到最终验收的完成内容，可作为提交描述、项目汇报或后续交接说明。

## 1. 本轮完成内容

### API 契约与后端接口

- 新增 `docs/api-contract.md`，覆盖 12 个核心接口的用途、请求示例、返回示例、字段说明和前端使用页面。
- 后端统一成功响应结构：`{ ok: true, data, error: null }`。
- 后端统一错误响应结构：`{ ok: false, data: null, error: { code, message, details } }`。
- 为 `HTTPException` 增加统一错误处理，404 job/resource 不再返回 FastAPI 默认 `detail` 结构。
- 补充后端接口契约测试，覆盖核心接口返回字段和错误响应。

### 前端接口与体验

- 补齐 `frontend/src/types.ts` 的核心类型，包括 `ApiResponse<T>`、`GenerationJob`、`ProfileChatResponse`、`TutorResponse` 等。
- 重写 `frontend/src/api.ts` 的返回类型，补齐 `job()` 和 `resource()` 详情接口。
- 更新 Pinia store，移除多余强制类型转换，增加 `refreshing`、`loading`、`assessing` 和全局 `error` 状态。
- 增加全局错误提示、页面刷新提示、空状态、按钮禁用和提交中状态。
- Tutor 页面去掉多余类型强转，增加提问中状态和局部错误提示。
- 优化工作台、Agent Trace、资源卡片、学习路径和测评报告展示，让页面更接近完整作品。
- 提取 `ResourceContent` 公共组件，统一资源详情渲染。
- Markdown 渲染支持标题、列表、表格和基础加粗；Mermaid 改为按需加载。
- Store 增加 `initialized` 和 `ensureReady()`，减少页面切换时的重复刷新请求。

### 后端稳定性与内容质量

- 启动时恢复 `profile`、`job`、`resource`、`learning_path`、`assessment_report` 状态。
- 资源生成任务增加 `queued/running/completed/failed` 生命周期和事件落库。
- 请求字段增加基础边界校验，错误响应保持统一 envelope。
- 生成内容升级为更像教学产品的材料：讲解表格、分层练习、视频分镜、代码实验、阅读路线。
- 学习路径推荐理由和测评报告反馈更具体，能支撑答辩演示。

### 交付文档与演示材料

- 新增最终检查清单：`docs/delivery/final-checklist.md`。
- 新增演示 Runbook：`docs/delivery/demo-runbook.md`。
- 重写 7 分钟演示脚本：`docs/delivery/demo-video-script.md`。
- 重写 PPT 大纲：`docs/delivery/ppt-outline.md`。
- 新增答辩手册：`docs/delivery/presentation-and-defense-guide.md`。
- 更新 `docs/README.md`，补充 API 契约、检查清单、演示脚本、PPT 大纲和答辩手册入口。

## 2. 验证结果

后端测试：

```text
cd backend
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider

6 passed
```

前端构建：

```text
cd frontend
npm run build

通过
```

说明：Mermaid 已按需加载，前端生产构建通过。

## 3. 当前可演示闭环

推荐演示顺序：

1. `/` 工作台
2. `/profile` 学习画像
3. `/generate` 资源生成和 Agent Trace
4. `/resources` 资源库和资源详情
5. `/path` 个性化学习路径
6. `/tutor` 智能辅导
7. `/assessment` 练习评估和路径调整
8. `/` 回到工作台收尾

核心讲解主线：

```text
对话画像 -> 多智能体资源生成 -> 资源库 -> 学习路径 -> 智能辅导 -> 练习评估 -> 路径调整
```

## 4. 需要注意的已知限制

- 当前使用 MockLLMProvider，适合稳定演示；真实大模型 Provider 是后续扩展方向。
- 资源生成当前同步完成，但接口结构已经保留 job、status、progress 和 events。
- 当前是单用户 MVP，多用户、登录权限和完整资源管理后台未实现。
- Markdown 和 Mermaid 渲染满足演示需求，但后续可替换为更完整的渲染库和安全策略。

## 5. 建议提交信息

```text
feat: align API contract and polish demo-ready learning workflow

- add API contract and final delivery checklist
- type frontend API calls and store state
- add loading, empty and error states for demo pages
- unify backend error envelope
- expand backend contract tests
- add demo script, PPT outline and defense guide
- improve backend state recovery and content quality
- extract shared resource renderer and lazy-load Mermaid
```

## 6. 下一阶段建议

如果继续完善项目，建议优先级如下：

1. 把资源生成改成真正后台异步任务和 SSE 进度推送。
2. 接入真实大模型 Provider，并增加 RAG 检索和事实校验。
3. 增加多用户、登录认证和权限管理。
4. 增加课程知识库管理页面。
5. 增加浏览器自动化端到端测试。
