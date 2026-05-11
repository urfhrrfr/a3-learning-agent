"""学习路径规划系统提示词"""

PATH_PLANNING_SYSTEM_PROMPT = """你是一位专业的学习路径规划专家。请根据学生画像生成个性化学习路径。

## 输出格式
必须严格输出JSON格式，不要其他文字：
```json
{
  "learning_path": {
    "id": "path_001",
    "profile_version": 1,
    "mastery": 0.5,
    "overall_goal": "...",
    "adjustment_reason": "...",
    "steps": [
      {
        "id": "step_01",
        "title": "...",
        "objective": "...",
        "estimated_minutes": 30,
        "status": "todo",
        "expected_mastery_increase": 0.1
      }
    ]
  },
  "confidence": 0.88,
  "reasoning": "规划说明"
}
```

## 规则
1. 步骤5-8步
2. 每步15-45分钟
3. 优先解决薄弱点
4. 考虑学习偏好和时间预算
"""


def build_path_planning_prompt(
    profile: dict,
    assessment: dict | None = None,
    available_resources: list[dict] | None = None,
    learning_history: list[dict] | None = None
) -> str:
    """构建路径规划提示词"""
    prompt = f"""{PATH_PLANNING_SYSTEM_PROMPT}

## 学生画像
学习目标: {profile.get('learning_goal', '')}
薄弱点: {', '.join(profile.get('weak_points', []))}
偏好模态: {', '.join(profile.get('preferred_modalities', []))}
时间预算: {profile.get('time_budget', '')}
知识基础: {', '.join(profile.get('knowledge_base', []))}
认知风格: {profile.get('cognitive_style', '')}
掌握度: {profile.get('mastery', 0.5)}

请生成个性化学习路径。"""
    return prompt


PATH_ADJUSTMENT_SYSTEM_PROMPT = """你是学习路径调整专家。根据评估结果调整路径。

输出JSON格式：
```json
{
  "adjusted_path": {学习路径},
  "adjustments": [{"type": "add/modify", "step_id": "...", "reason": "..."}],
  "confidence": 0.85,
  "reasoning": "调整说明"
}
```
"""


def build_path_adjustment_prompt(
    current_path: dict,
    assessment: dict,
    profile: dict,
    available_resources: list[dict] | None = None
) -> str:
    return f"""{PATH_ADJUSTMENT_SYSTEM_PROMPT}

当前路径: {current_path.get('steps', [])}
评估结果: {assessment}
学生画像: {profile}

请调整学习路径。"""


RESOURCE_PRIORITY_SYSTEM_PROMPT = """你是资源推荐专家。根据学生画像排序资源优先级。

输出JSON格式：
```json
{
  "prioritized_resources": [{"id": "...", "priority": 1, "score": 0.9}],
  "confidence": 0.88
}
```
"""


def build_resource_priority_prompt(profile: dict, assessment: dict, resources: list[dict]) -> str:
    return f"""{RESOURCE_PRIORITY_SYSTEM_PROMPT}

学生画像: {profile}
评估结果: {assessment}
资源列表: {resources}

请排序资源优先级。"""
