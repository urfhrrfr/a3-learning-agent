# Redis 可选缓存说明

本项目提交版默认使用 SQLite 做持久化，不强依赖 Redis。Redis 是可选增强层，用于展示更接近部署环境的任务状态缓存和快速恢复能力。

## 启用方式

不配置 `REDIS_URL` 时，系统自动使用 SQLite + 内存状态运行：

```env
REDIS_URL=
```

需要启用 Redis 时配置：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

## 缓存内容

- 生成任务进度：`job_id -> status/progress/current_step`
- Agent Trace 快照：用于展示多智能体执行过程
- 生成资源快照：用于降低重复读取和状态同步成本

任务查询接口会按以下顺序恢复任务状态：

```text
内存运行态 -> Redis 快照 -> SQLite 持久化
```

## 降级策略

Redis 未配置、连接失败或依赖不可用时，系统不会报错退出。后端仍然写入 SQLite，前端演示流程保持可用。

可通过 `GET /api/health` 查看缓存状态：

```json
{
  "cache": {
    "enabled": false,
    "available": false,
    "reason": "REDIS_URL not configured"
  }
}
```

## 答辩表述

> 提交版本采用 SQLite 保证零部署可复现，同时预留 Redis 作为可选缓存层，用于任务进度、Agent Trace 和热点资源快照。Redis 不可用时系统自动降级，不影响核心演示闭环。
