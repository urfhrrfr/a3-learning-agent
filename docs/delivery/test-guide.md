# 测试说明书

## 功能测试

验证画像对话、资源生成、资源列表、学习路径、辅导问答、练习提交和评估报告接口是否返回统一结构。

## 接口测试

后端使用 `pytest` 覆盖：

- `POST /api/profile/chat` 更新画像。
- `POST /api/resources/generate` 生成不少于 6 类资源和完整 Agent Trace。
- `POST /api/quiz/submit` 生成评估报告和调整路径。

## 前端交互测试

运行 `npm run build` 验证 TypeScript 和 Vue 构建。手动进入 `/`、`/profile`、`/generate`、`/resources`、`/path`、`/tutor`、`/assessment` 检查无白屏和无接口错误。

## 资源质量测试

抽查每个资源是否包含 `type`、`title`、`content_format`、`content`、`source_refs`、`difficulty`、`target_profile`、`review_status`、`created_by_agents`。

## 防幻觉测试

检查资源来源是否指向 `ai_intro/chxx#...`；检查 ReviewAgent 是否把无来源或不安全内容标记为 `needs_revision` 或 `blocked`。

## 性能与演示测试

Mock 模式下资源生成应在数秒内完成；前端生成页必须显示进度条和 Agent Trace，避免长任务白屏。

## 演示用例

1. 输入“我线性代数薄弱，希望多给 Python 代码案例和动画解释”。
2. 发起机器学习基础资源生成。
3. 查看 6 类资源和 Agent Trace。
4. 提交含“过拟合、泛化”的练习答案。
5. 查看评估报告和路径调整。
