# SeeDance 多模态视频接入方案

## 目标

把当前 `media_script` 从“视频脚本资源”升级为“脚本 + 生成任务 + 视频预览”的闭环，用于支撑演示中的知识点动画讲解、实操步骤演示视频。

## 当前基础

- `MediaAgent` 已能生成分镜脚本，内容包含时间、画面、旁白、屏幕文字。
- 资源生成已经支持后台 job 和 SSE 事件，前端能显示每个智能体的实时完成进度。
- `ResourceContent` 已能按资源格式渲染 Markdown、Mermaid、JSON 和代码内容。

## 推荐接入位置

后端新增独立视频服务层：

```text
backend/app/video/
  base.py              # VideoProvider 抽象接口
  factory.py           # 根据 VIDEO_PROVIDER 选择 mock/seedance
  mock_video.py        # 本地演示兜底，返回示例视频状态
  seedance.py          # SeeDance HTTP API 适配
```

新增数据模型：

```text
VideoJob
- id
- resource_id
- provider
- status: queued/running/completed/failed
- prompt
- storyboard
- progress
- video_url
- preview_url
- error
- created_at
- completed_at
```

新增接口：

```text
POST /api/videos/generate
GET  /api/videos/{video_job_id}
GET  /api/videos/{video_job_id}/events
```

## 前端演示形态

在资源详情页识别 `media_script`，显示“生成讲解视频”按钮。点击后：

1. 创建视频任务。
2. 用 SSE 展示“解析分镜、提交 SeeDance、等待渲染、视频生成完成”。
3. 成功后在资源详情页内嵌 `<video controls>` 预览。
4. 失败时保留脚本资源，并提示可重新生成。

## 环境变量

```text
VIDEO_PROVIDER=mock | seedance
SEEDANCE_API_KEY=
SEEDANCE_BASE_URL=
SEEDANCE_MODEL=
SEEDANCE_CALLBACK_URL=
```

## 兜底策略

比赛现场优先保证稳定演示：

- 无密钥或接口不可用时，`mock_video` 返回固定可预览视频或“分镜动画预览”。
- 真实 SeeDance 生成失败时，前端保留分镜脚本和错误信息，不影响主学习闭环。
- 视频任务与资源生成任务解耦，避免视频耗时拖慢 5 类核心资源生成。

## 下一步实现顺序

1. 加 `VideoJob` 模型、存储和 mock provider。
2. 在 `ResourceContent` 为 `media_script` 增加视频生成按钮和进度区域。
3. 接真实 SeeDance provider。
4. 在 Demo Runbook 中加入“生成动画讲解视频”的备用路线：真实接口成功走视频预览，失败走分镜动画预览。
