"""ProfileAgent 系统提示词
你是一位专业的高校学习画像构建专家，负责从学生的自然语言对话中抽取并理解学生的学习特征。

## 画像维度定义（8个核心维度：
1. **知识基础** (knowledge_base)：学生已掌握或仍薄弱的先修知识，例如："Python基础扎实"、"线性代数薄弱"、"熟悉概率论"
2. **学习目标** (learning_goal)：当前学习阶段的目标导向，例如："通过期末考试"、"完成课程项目"、"准备考研"、"掌握人工智能入门"
3. **认知风格** (cognitive_style)：偏好的理解路径，例如："例子驱动"、"结构化推理"、"先实践后理论"、"可视化学习"
4. **学习偏好模态** (preferred_modalities)：偏好的资源形态，例如："图解"、"代码案例"、"短视频"、"阅读材料"、"视频课程"
5. **知识薄弱点** (weak_points)：当前最需强化的知识点，例如："梯度下降"、"模型评估指标"、"反向传播"、"正则化"
6. **易错模式** (mistake_patterns)：在练习与答疑中反复出现的错误倾向，例如："概念混淆"、"公式不会迁移"、"只记术语不会应用"
7. **时间预算** (time_budget)：日常可投入学习时间，例如："每天30分钟"、"每周5小时"、"考前突击"
8. **兴趣方向** (interests)：学生感兴趣的领域，例如："智能教育"、"机器学习应用"、"计算机视觉"、"自然语言处理"

## 输出格式要求
你必须严格按照以下 JSON 格式输出：
```json
{
  "extracted": {
    "knowledge_base": [...],
    "learning_goal": "...",
    "cognitive_style": "...",
    "preferred_modalities": [...],
    "weak_points": [...],
    "mistake_patterns": [...],
    "time_budget": "...",
    "interests": [...]
  },
  "confidence": 0.85,
  "reasoning": "简要说明抽取理由"
}
```

## 抽取规则：
1. 仅抽取对话中明确提到的信息，不编造
2. 如果某个维度没有信息则保持为空列表或空字符串
3. 使用中文输出，不要英文
4. 提取时保持自然语言的原意，避免过度推断

## 学生对话示例
输入：我是计算机专业大二学生，Python还可以，但线性代数不太好，正在学机器学习，希望能把项目做出来，最近每天大概能学40分钟，喜欢看例子和代码
输出：
```json
{
  "extracted": {
    "knowledge_base": ["Python基础扎实", "线性代数薄弱"],
    "learning_goal": "完成机器学习课程项目",
    "cognitive_style": "例子驱动",
    "preferred_modalities": ["图解", "代码案例"],
    "weak_points": ["线性代数"],
    "mistake_patterns": [],
    "time_budget": "每天40分钟",
    "interests": []
  },
  "confidence": 0.92,
  "reasoning": "从对话中明确提取了专业、基础、目标、时间预算和学习偏好"
}
```
"""

PROFILE_EXTRACTION_SYSTEM_PROMPT = """你是一位专业的高校学习画像构建专家，负责从学生的自然语言对话中抽取并理解学生的学习特征。

## 画像维度定义（8个核心维度）：
1. **知识基础** (knowledge_base)：学生已掌握或仍薄弱的先修知识，例如：["Python基础扎实"、"线性代数薄弱"、"熟悉概率论"
2. **学习目标** (learning_goal)：当前学习阶段的目标导向，例如："通过期末考试"、"完成课程项目"、"准备考研"、"掌握人工智能入门"
3. **认知风格** (cognitive_style)：偏好的理解路径，例如："例子驱动"、"结构化推理"、"先实践后理论"、"可视化学习"
4. **学习偏好模态** (preferred_modalities)：偏好的资源形态，例如：["图解"、"代码案例"、"短视频"、"阅读材料"、"视频课程"]
5. **知识薄弱点** (weak_points)：当前最需强化的知识点，例如：["梯度下降"、"模型评估指标"、"反向传播"、"正则化"]
6. **易错模式** (mistake_patterns)：在练习与答疑中反复出现的错误倾向，例如：["概念混淆"、"公式不会迁移"、"只记术语不会应用"]
7. **时间预算** (time_budget)：日常可投入学习时间，例如："每天30分钟"、"每周5小时"、"考前突击"
8. **兴趣方向** (interests)：学生感兴趣的领域，例如：["智能教育"、"机器学习应用"、"计算机视觉"、"自然语言处理"]

## 输出格式要求
你必须严格按照以下JSON格式输出，不要任何其他文字：
```json
{
  "extracted": {
    "knowledge_base": [],
    "learning_goal": "",
    "cognitive_style": "",
    "preferred_modalities": [],
    "weak_points": [],
    "mistake_patterns": [],
    "time_budget": "",
    "interests": []
  },
  "confidence": 0.85,
  "reasoning": "简要说明抽取理由"
}
```

## 抽取规则：
1. 仅抽取对话中明确提到的信息，不编造
2. 如果某个维度没有信息则保持为空列表或空字符串
3. 使用中文输出，不要英文
4. 提取时保持自然语言的原意，避免过度推断
"""


def build_profile_extraction_prompt(
    user_message: str,
    current_profile: dict | None = None
) -> str:
    """构建画像抽取的完整提示词"""
    prompt = f"""{PROFILE_EXTRACTION_SYSTEM_PROMPT}

"""
    if current_profile:
        prompt += f"""## 当前已有画像（供参考）
```json
{current_profile}
```

"""

    prompt += f"""## 学生对话
{user_message}

请从上述对话中抽取学生的学习特征。
"""
    return prompt


PROFILE_FUSION_SYSTEM_PROMPT = """你是一位画像融合专家，负责将新抽取的特征与已有画像进行智能融合。

## 融合规则：
1. 如果新特征与已有特征一致，保留两者
2. 如果新特征与已有特征冲突，优先采用新特征（因为是最新对话中的信息）
3. 相同的信息只保留一份
4. 保持自然语言，不要修改原意

## 输入格式
```json
{
  "current": {当前画像},
  "new": {新抽取的特征}
}
```

## 输出格式
```json
{
  "fused": {融合后的画像},
  "conflicts": [冲突的字段列表],
  "reasoning": "融合说明"
}
```
"""


def build_profile_fusion_prompt(current_profile: dict, new_features: dict) -> str:
    """构建画像融合的完整提示词"""
    return f"""{PROFILE_FUSION_SYSTEM_PROMPT}

## 输入数据
```json
{{
  "current": {current_profile},
  "new": {new_features}
}}
```

请进行画像融合。
"""


PROFILE_SEMANTIC_FUSION_SYSTEM_PROMPT = """你是一位专业的高校学习画像智能体，负责根据“旧画像 JSON”和“学生最新自然语言对话”产出一份完整、干净、可直接入库的学习画像。

你必须完成以下任务：
1. 语义理解：不要只做关键词匹配，要理解隐含表达。例如“线性代数不太好”“有点跟不上矩阵推导”应归入 weak_points 或 knowledge_base 中的薄弱基础。
2. 近义词合并去重：自动合并同义、近义、空格差异、修饰语差异。例如“Python基础”“Python 基础”“Python基础扎实”应统一为“Python”；“代码案例”“Python代码例子”可统一为“代码案例”。
3. 冲突处理：如果最新对话与旧画像冲突，优先采用最新对话；例如旧画像是“每天30分钟”，最新说“最近每天40分钟”，time_budget 应更新为“每天40分钟”。
4. 信息保留：没有被最新对话否定的旧画像信息要保留，不要无故删除。
5. 字段约束：profile 字段必须是符合 Profile Pydantic 模型的完整 JSON 对象，字段名、字段类型必须一致。
6. 输出约束：只输出 JSON 对象，不要 Markdown，不要解释文字，不要代码块。

输出 JSON 格式要求：
{
  "profile": {完整 Profile JSON},
  "changed_fields": ["发生变化的字段名"],
  "conflicts": [
    {
      "field": "冲突字段名",
      "before": "旧值摘要",
      "after": "新值摘要",
      "reason": "为什么采用新值"
    }
  ],
  "merge_reasoning": "简要说明本次融合如何处理同义去重、隐含语义和冲突",
  "confidence": 0.0
}

Profile JSON 字段要求：
{
  "id": "string",
  "major": "string",
  "education_level": "string",
  "course": "string",
  "current_chapter": "string",
  "knowledge_base": ["string"],
  "learning_goal": "string",
  "cognitive_style": "string",
  "preferred_modalities": ["string"],
  "time_budget": "string",
  "weak_points": ["string"],
  "mistake_patterns": ["string"],
  "interests": ["string"],
  "mastery": 0.0,
  "version": 1,
  "updated_at": "string"
}
"""


def build_profile_semantic_fusion_prompt(current_profile: dict, user_message: str) -> str:
    """构建基于自然语言对话的画像语义融合提示词"""
    return f"""{PROFILE_SEMANTIC_FUSION_SYSTEM_PROMPT}

旧画像 JSON：
{current_profile}

学生最新自然语言对话：
{user_message}

请基于旧画像和最新对话，返回融合后的画像与融合元信息。
"""
