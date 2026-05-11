# 多智能体协同证据（Trace）

## 协同链路

`Knowledge -> Planner -> Producers -> Review -> Path`

其中 Producers 包含：

- `LectureAgent`
- `MindMapAgent`
- `QuizAgent`
- `ReadingAgent`
- `MediaAgent`
- `PPTDraftAgent`
- `VisualCardAgent`
- `CodeCaseAgent`

## Trace 字段说明（用于答辩展示）

- `input_summary`：本智能体输入摘要
- `output_summary`：本智能体输出摘要
- `source_refs`：证据来源章节锚点
- `confidence`：执行置信度
- `collaboration_stage`：协作阶段（knowledge/planning/producer/review）
- `boundary`：分工边界说明
- `depends_on`：上游依赖节点
- `retry_count`：失败重试次数
- `arbitration_note`：冲突仲裁说明（由 ReviewAgent 输出）
- `review_conclusion`：审核结论（通过/需修改/拦截统计）

## 真实 Trace 示例（节选）

```json
{
  "agent": "ReviewAgent",
  "input_summary": "机器学习基础 / 理解泛化与过拟合",
  "output_summary": "审核 8 份资源，passed=8，needs_revision=0，blocked=0",
  "source_refs": [
    "ai_intro/ch04#objectives",
    "ai_intro/ch04#detailed_concepts",
    "ai_intro/ch04#misconceptions",
    "ai_intro/ch04#real_cases"
  ],
  "confidence": 0.91,
  "collaboration_stage": "review",
  "boundary": "负责审核与仲裁，不负责新增资源内容",
  "depends_on": [
    "KnowledgeAgent",
    "LectureAgent",
    "QuizAgent",
    "ReadingAgent",
    "MediaAgent",
    "PPTDraftAgent",
    "VisualCardAgent",
    "CodeCaseAgent"
  ],
  "retry_count": 0,
  "arbitration_note": "冲突仲裁规则：来源缺失优先判定 needs_revision；安全风险优先判定 blocked；其余按相关性判定。",
  "review_conclusion": "最终结论：passed=8，needs_revision=0，blocked=0"
}
```
