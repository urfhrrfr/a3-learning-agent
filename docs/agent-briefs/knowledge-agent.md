# Knowledge Base Agent Brief

## Mission

构造一门完整高校课程的初始知识库，作为系统 RAG 与资源生成的输入。推荐课程是 `人工智能导论`。

## Read First

- `docs/project-blueprint.md`
- `docs/agent-execution-pack.md`

## Ownership

你负责课程内容、导入格式和样例数据。不负责后端 API 和前端页面。

## Required Course Structure

课程：人工智能导论

章节：

1. 人工智能概述
2. 搜索问题与启发式搜索
3. 知识表示与推理
4. 机器学习基础
5. 监督学习
6. 无监督学习
7. 神经网络与深度学习入门
8. 自然语言处理基础
9. 计算机视觉基础
10. 强化学习基础
11. 大模型与提示词工程
12. AI 伦理、安全与应用实践

每章至少包含：

- 学习目标
- 核心概念
- 重点难点
- 常见误区
- 示例讲解
- 练习题草案
- 拓展阅读建议
- 实践任务建议

## Suggested File Format

建议目录：

```text
backend/data/courses/ai_intro/
  course.yaml
  chapters/
    01-ai-overview.md
    02-search.md
    03-knowledge-representation.md
    ...
  examples/
    search_a_star.py
    ml_classification.py
```

`course.yaml` 示例：

```yaml
id: ai_intro
title: 人工智能导论
level: undergraduate
language: zh-CN
chapters:
  - id: ch01
    title: 人工智能概述
    file: chapters/01-ai-overview.md
```

Markdown 每章建议格式：

```markdown
# 章节标题

## 学习目标

## 核心概念

## 重点难点

## 常见误区

## 示例讲解

## 练习题草案

## 拓展阅读建议

## 实践任务建议
```

## Content Rules

- 内容必须适合本科生。
- 不要写无法核实的具体事实。
- 专业概念要准确，但表达要适合教学。
- 每章都要能支撑资源生成。
- 代码案例尽量使用 Python 标准库、numpy、scikit-learn 等常见工具；如果使用额外依赖，需要标注。

## Acceptance Criteria

- 至少 12 章课程文档。
- 每章内容结构一致。
- 至少 3 个 Python 实操案例主题。
- 至少 60 道题目草案，覆盖选择、判断、简答、代码理解。
- 每个知识块可以被切分并追踪来源 ID。

