# QA, Docs and Demo Agent Brief

## Mission

准备比赛交付所需的测试、文档、PPT 大纲和 7 分钟演示视频脚本，确保项目不只是能跑，还能被评委快速理解。

## Read First

- `docs/project-blueprint.md`
- `docs/agent-execution-pack.md`

## Ownership

你负责：

- 测试说明
- 系统开发说明
- 部署说明
- 开源组件与协议说明
- AI Coding 工具说明
- PPT 大纲
- 演示视频脚本

你不负责：

- 后端核心代码
- 前端核心代码
- 课程知识库正文

## Required Documents

建议输出：

```text
docs/delivery/
  system-development-guide.md
  test-guide.md
  deployment-guide.md
  open-source-and-ai-tools.md
  ppt-outline.md
  demo-video-script.md
```

## System Development Guide Outline

必须覆盖：

- 项目背景与痛点
- 用户需求分析
- 系统总体架构
- 多智能体协同设计
- 学习画像设计
- 资源生成流程
- RAG 与防幻觉机制
- 内容安全机制
- 前后端设计
- 数据库设计
- 测试与部署
- 创新点总结

## Test Guide Outline

必须覆盖：

- 功能测试
- 接口测试
- 前端交互测试
- 资源生成质量测试
- 防幻觉测试
- 内容安全测试
- 性能与响应时间测试
- 演示用例测试

## PPT Outline

建议 12 页以内：

1. 题目与团队
2. 背景痛点
3. 解决方案总览
4. 系统架构
5. 多智能体协同机制
6. 对话式学习画像
7. 个性化资源生成效果
8. 学习路径与智能推送
9. 智能辅导与学习评估
10. 防幻觉、安全与性能设计
11. 创新价值与应用前景
12. 总结与演示入口

## 7-Minute Demo Script

建议时间分配：

- 0:00-0:40 背景痛点与系统目标
- 0:40-1:30 对话式画像构建
- 1:30-3:20 多智能体资源生成和 trace
- 3:20-4:30 资源库展示
- 4:30-5:20 学习路径和推荐理由
- 5:20-6:20 练习评估与路径调整
- 6:20-7:00 防幻觉、安全、总结

## Open Source and AI Tools Notes

必须记录：

- Python、FastAPI、Vue、Vite 等开源组件名称
- 版本
- 来源链接
- 协议
- 用途
- AI Coding 工具使用说明
- 科大讯飞相关模型或工具的使用说明

具体模型和 API 信息不要凭记忆写死，提交前应以官方文档核对。

## Acceptance Criteria

- 文档能直接放入初赛提交包。
- PPT 大纲能覆盖评分项。
- 视频脚本能在 7 分钟内讲清核心功能。
- 测试说明能证明系统不是纯 Demo。
- 开源和 AI 工具说明清晰可审查。

