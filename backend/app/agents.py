from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .knowledge import find_chapter
from .providers.mock_llm import MockLLMProvider
from .schemas import AgentTrace, GenerateRequest, Profile, Resource


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class WorkflowState:
    def __init__(self, job_id: str, request: GenerateRequest, profile: Profile):
        self.job_id = job_id
        self.request = request
        self.profile = profile
        self.chapter = find_chapter(request.chapter)
        self.sources = [f"{self.chapter['id']}#overview", f"{self.chapter['id']}#practice"]
        self.resources: list[Resource] = []
        self.traces: list[AgentTrace] = []
        self.plan: list[str] = []


class Agent:
    name = "Agent"
    role = "base"

    def __init__(self, llm: MockLLMProvider | None = None):
        self.llm = llm or MockLLMProvider()

    def run(self, state: WorkflowState) -> dict:
        return {}

    def traced_run(self, state: WorkflowState, input_summary: str) -> AgentTrace:
        trace = AgentTrace(
            id=f"trace_{uuid4().hex[:8]}",
            job_id=state.job_id,
            agent=self.name,
            status="running",
            input_summary=input_summary,
            output_summary="",
            source_refs=list(state.sources),
            confidence=0.84,
            started_at=now(),
        )
        result = self.run(state)
        trace.status = "completed"
        trace.output_summary = result.get("summary", f"{self.name} 已完成")
        trace.warnings = result.get("warnings", [])
        trace.confidence = result.get("confidence", trace.confidence)
        trace.finished_at = now()
        state.traces.append(trace)
        return trace


class ProfileAgent(Agent):
    name = "ProfileAgent"
    role = "从对话抽取画像"


class KnowledgeAgent(Agent):
    name = "KnowledgeAgent"
    role = "检索课程知识库"

    def run(self, state: WorkflowState) -> dict:
        state.sources = [f"{state.chapter['id']}#concepts", f"{state.chapter['id']}#misconceptions"]
        return {"summary": f"检索到 {state.chapter['title']} 的目标、概念、误区和练习草案"}


class PlannerAgent(Agent):
    name = "PlannerAgent"
    role = "规划资源组合"

    def run(self, state: WorkflowState) -> dict:
        state.plan = ["lecture_doc", "mind_map", "quiz", "reading", "media_script", "code_case"]
        return {"summary": "规划 6 类资源：讲解、导图、练习、阅读、视频脚本、代码案例"}


class ResourceAgent(Agent):
    resource_type = "lecture_doc"
    content_format = "markdown"
    title_prefix = "资源"

    def content(self, state: WorkflowState) -> str:
        return f"# {self.title_prefix}\n\n基于 {state.chapter['title']} 生成。"

    def run(self, state: WorkflowState) -> dict:
        resource = Resource(
            id=f"res_{uuid4().hex[:8]}",
            type=self.resource_type,
            title=f"{self.title_prefix}：{state.chapter['title']}",
            content_format=self.content_format,
            content=self.content(state),
            source_refs=list(state.sources),
            difficulty="入门到提高",
            target_profile=[state.profile.cognitive_style, *state.profile.preferred_modalities[:2]],
            review_status="needs_revision",
            created_by_agents=["KnowledgeAgent", self.name],
            created_at=now(),
        )
        state.resources.append(resource)
        return {"summary": f"生成资源 {resource.title}"}


class LectureAgent(ResourceAgent):
    name = "LectureAgent"
    resource_type = "lecture_doc"
    title_prefix = "课程讲解文档"

    def content(self, state: WorkflowState) -> str:
        concepts = "、".join(state.chapter["concepts"])
        return (
            f"# {state.chapter['title']} 个性化讲解\n\n"
            f"## 学习目标\n- {state.request.goal}\n- 用例子理解 {concepts}\n\n"
            f"## 核心概念\n{concepts}\n\n"
            f"## 易错提醒\n- {state.chapter['misconceptions'][0]}\n- 对线性代数薄弱的同学，先关注输入输出和图像直觉。\n\n"
            "## 例子\n用校园课程推荐来类比：数据是学习记录，模型学习偏好，评价指标检查推荐是否有效。\n"
        )


class MindMapAgent(ResourceAgent):
    name = "MindMapAgent"
    resource_type = "mind_map"
    content_format = "mermaid"
    title_prefix = "Mermaid 思维导图"

    def content(self, state: WorkflowState) -> str:
        nodes = "\n".join([f"  A --> C{i}[{c}]" for i, c in enumerate(state.chapter["concepts"], start=1)])
        return f"mindmap\n  root(({state.chapter['title']}))\n    学习目标\n    核心概念\n{nodes}\n    常见误区\n    实践任务"


class QuizAgent(ResourceAgent):
    name = "QuizAgent"
    resource_type = "quiz"
    content_format = "json"
    title_prefix = "分层练习题"

    def content(self, state: WorkflowState) -> str:
        return """[
  {"level":"基础","question":"什么是训练集与测试集？","answer":"训练集用于拟合模型，测试集用于估计泛化表现。"},
  {"level":"应用","question":"为什么只看训练准确率可能误导？","answer":"可能发生过拟合，无法反映新数据表现。"},
  {"level":"提高","question":"给定混淆矩阵，如何解释精确率与召回率？","answer":"精确率关注预测为正的可靠性，召回率关注真实为正被找回的比例。"}
]"""


class ReadingAgent(ResourceAgent):
    name = "ReadingAgent"
    resource_type = "reading"
    title_prefix = "拓展阅读材料"

    def content(self, state: WorkflowState) -> str:
        return "## 阅读建议\n1. 教材对应章节：先读概念定义。\n2. 课程讲义案例：关注输入、输出、评价。\n3. 实验说明：用小数据复现实验。\n\n每段阅读后写一句“我能用什么例子说明它”。"


class MediaAgent(ResourceAgent):
    name = "MediaAgent"
    resource_type = "media_script"
    title_prefix = "视频/动画脚本"

    def content(self, state: WorkflowState) -> str:
        return "## 3 分钟动画脚本\n- 0:00 学生面对混乱知识点。\n- 0:40 用图示拆分数据、模型、评价。\n- 1:40 展示一个预测例子。\n- 2:30 总结常见误区和练习入口。"


class CodeCaseAgent(ResourceAgent):
    name = "CodeCaseAgent"
    resource_type = "code_case"
    content_format = "code"
    title_prefix = "Python 代码实操案例"

    def content(self, state: WorkflowState) -> str:
        return """# 机器学习基础：最近邻分类小实验（仅标准库）
samples = [([0, 0], "基础"), ([1, 1], "基础"), ([5, 5], "提高"), ([6, 5], "提高")]
query = [2, 2]

def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

nearest = min(samples, key=lambda item: distance(item[0], query))
print("预测层级:", nearest[1])
"""


class ReviewAgent(Agent):
    name = "ReviewAgent"
    role = "审核事实、来源、难度与安全"

    def run(self, state: WorkflowState) -> dict:
        blocked = 0
        for resource in state.resources:
            if not resource.source_refs:
                resource.review_status = "needs_revision"
            elif "违法" in resource.content:
                resource.review_status = "blocked"
                blocked += 1
            else:
                resource.review_status = "passed"
            if "ReviewAgent" not in resource.created_by_agents:
                resource.created_by_agents.append("ReviewAgent")
        return {"summary": f"审核 {len(state.resources)} 份资源，blocked={blocked}", "confidence": 0.9}


class AssessmentAgent(Agent):
    name = "AssessmentAgent"
    role = "评估学习效果并调整路径"


class Orchestrator:
    def __init__(self):
        self.agents = [
            KnowledgeAgent(),
            PlannerAgent(),
            LectureAgent(),
            MindMapAgent(),
            QuizAgent(),
            ReadingAgent(),
            MediaAgent(),
            CodeCaseAgent(),
            ReviewAgent(),
        ]

    def generate(self, job_id: str, request: GenerateRequest, profile: Profile):
        state = WorkflowState(job_id, request, profile)
        for agent in self.agents:
            agent.traced_run(state, f"{request.chapter} / {request.goal}")
            yield agent, state
