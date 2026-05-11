# ProfileAgent 增强方案说明
================================

## 概述

本次增强实现了完整的对话式学习画像构建功能，主要包括：

1. **提示词工程 (prompts.py)
2. **完整的 ProfileAgent 实现
3. **画像冲突检测与融合机制
4. **后端集成与 API 增强

## 文件结构
-----------

```
backend/app/
├── prompts.py          # 新增：提示词工程模块
├── agents.py       # 修改：ProfileAgent 完整实现
├── state.py        # 修改：集成 ProfileAgent
└── routes.py       # 修改：增强 API 返回数据
```

## 提示词设计
------------

### PROFILE_EXTRACTION_SYSTEM_PROMPT

- 画像抽取的系统提示词

主要特点：
- 明确了 8 个核心维度的定义
- 清晰的输出格式要求（JSON）
- 包含学生对话示例
- 详细的抽取规则

### PROFILE_FUSION_SYSTEM_PROMPT

- 画像融合的系统提示词

主要特点：
- 融合规则说明
- 冲突处理策略
- 输入输出格式

## ProfileAgent 功能
-----------------

### 核心方法

#### `extract(message, current_profile)`

从对话中抽取特征

**流程：**
1. 尝试使用 LLM 抽取（优先使用科大讯飞星火）
2. 解析 LLM 响应，提取 JSON
3. 检查置信度，低于阈值则使用后备方案
4. 返回抽取结果，包含置信度和来源信息

**返回数据结构：
```python
{
    "extracted": {...},        # 抽取的特征
    "confidence": 0.9,    # 置信度
    "reasoning": "...",      # 推理说明
    "source": "llm" | "fallback"
}
```

#### `_fallback_extract(message)

后备抽取方法（基于关键词）

覆盖的关键词：
- 知识基础：数学、线代、Python
- 学习目标：考研、考试、项目
- 认知风格：例子、结构、实践
- 偏好模态：图解、代码、视频、阅读
- 薄弱点：梯度、评估、反向传播
- 时间预算：每天/每周 + 时间
- 兴趣：教育、机器学习、视觉、NLP

#### `fuse(current_profile, extracted)`

融合新抽取的特征

**融合策略：**
- 列表字段：合并去重，新值优先
- 字符串字段：新值覆盖旧值（检测冲突
- 检测冲突并记录

**返回：**
- fused_profile  # 融合后的画像
- conflicts      # 冲突列表
- reasoning    # 融合说明

## 冲突检测
----------

### 冲突字段

目前检测以下字段的冲突：
- `learning_goal`
- `time_budget`
- `cognitive_style`

### 冲突处理规则

当检测到冲突时：
1. 记录冲突信息
2. 使用新抽取的特征
3. 在返回数据中包含冲突详情

## API 增强
---------

### POST `/api/profile/chat`

增强的返回数据：

```json
{
  "profile": {...},
  "extracted": {...},
  "confidence": 0.9,
  "source": "llm",
  "reasoning": "...",
  "conflicts": [...],
  "fusion_reason": "...",
  "changed_fields": {...},
  "suggested_next_questions": [...]
}
```

## 使用说明
----------

### 配置科大讯飞星火

配置 `.env` 文件：

```
LLM_PROVIDER=spark
SPARK_APP_ID=your_app_id
SPARK_API_KEY=your_api_key
SPARK_API_SECRET=your_api_secret
SPARK_MODEL=generalv3.5
```

### 测试

运行测试脚本：

```bash
cd backend
python test_profile.py
```

## 扩展性
--------

### 扩展关键词

编辑 `ProfileAgent._fallback_extract` 方法，添加新的关键词匹配规则。

### 扩展维度

在 `prompts.py` 中更新画像维度定义，同时更新：
1. 更新 `schemas.Profile` 类
2. 更新 `state.PROFILE_DIMENSIONS`
3. 更新 `_fallback_extract` 后备方法

## 示例对话示例
------------

### 学生输入

```
"我是计算机专业大二学生，Python还可以，但线性代数不太好，正在学机器学习，希望能把项目做出来，最近每天大概能学40分钟，喜欢看例子和代码"
```

### 抽取结果

```json
{
  "extracted": {
    "knowledge_base": ["Python基础扎实", "线性代数薄弱"],
    "learning_goal": "完成课程项目",
    "cognitive_style": "例子驱动",
    "preferred_modalities": ["图解", "代码案例"],
    "weak_points": ["线性代数"],
    "time_budget": "每天40分钟"
  },
  "confidence": 0.92,
  "reasoning": "从对话中明确提取了专业、基础、目标、时间预算和学习偏好",
  "source": "llm"
}
```
