from __future__ import annotations

import json
import re
from html import escape
from uuid import uuid4

from ..base import Agent, WorkflowState, bullets, now, parse_llm_json
from ...assessment_prompts import build_assessment_prompt, build_review_fact_check_prompt
from ...core.profile_normalizer import ProfileNormalizer
from ...core.profile_validator import ProfileValidator
from ...knowledge import COURSE, find_chapter
from ...providers.base import BaseLLMProvider, LLMProviderError
from ...providers.factory import get_llm_provider
from ...prompts import (
    build_profile_extraction_prompt,
    build_profile_semantic_fusion_prompt,
)
from ...pptx_renderer import PPTXRenderError, render_pptx_deck
from ...retrieval import HybridRetriever, save_retrieval_log
from ...schemas import AgentTrace, GenerateRequest, Profile, Resource
from .base import ResourceAgent


class MediaAgent(ResourceAgent):
    name = "MediaAgent"
    resource_type = "media_script"
    title_prefix = "视频/动画脚本"
    stage = "producer"
    boundary = "只输出分镜脚本，不直接调用多模态引擎"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        case_hint = state.chapter["real_cases"][0]
        concept = state.chapter["concepts"][0]
        return (
            "## 3 分钟微课分镜脚本\n\n"
            "| 时间 | 画面 | 旁白 | 屏幕文字 |\n"
            "| --- | --- | --- | --- |\n"
            "| 0:00-0:20 | 学生盯着“训练集、泛化、过拟合”三个词，画面有问号。 | 学机器学习时，最容易混的是：模型到底学到了规律，还是只记住了题目？ | 今天解决：训练表现 vs 泛化表现 |\n"
            "| 0:20-0:55 | 左侧出现课堂练习，右侧出现新试卷。 | 训练集像课堂练习，测试集像新试卷。练习做得好，不代表新试卷一定好。 | 训练集：学习；测试集：检验 |\n"
            "| 0:55-1:30 | 推荐系统给老用户推荐正确，给新用户推荐失准。 | 如果模型只记住老用户的偏好，新用户一来就容易出错，这就是过拟合的直观表现。 | 过拟合：记住样本，迁移变差 |\n"
            "| 1:30-2:10 | 图表展示训练准确率上升、测试准确率下降。 | 判断模型不能只看训练准确率，要同时看新数据上的表现。 | 关注泛化，而不只关注背题 |\n"
            "| 2:10-2:40 | 展示三个检查清单：拆分数据、选指标、看反例。 | 真实任务里，我们用数据拆分、评价指标和错误案例一起判断模型是否可靠。 | 三步检查法 |\n"
            "| 2:40-3:00 | 回到学生，知识点变成流程图。 | 现在你可以用一个自己的例子解释过拟合，并设计一个验证方法。 | 课后任务：造例子 + 说验证 |\n\n"
            "### 拍摄/制作提示\n"
            "- 风格：白板动画 + 简单数据图。\n"
            "- 互动点：1:30 暂停，让学生判断是否过拟合。\n"
            "- 配套练习：完成 1 道判断题和 1 道场景解释题。\n"
            f"- 优先改编案例：{case_hint}\n\n"
            "### 多模态生成预留参数\n"
            f"- visual_style: 扁平化教学动画\n- key_concept: {concept}\n- sync_to_tool: 预留给后续图像/语音/视频生成工具"
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授和教学视频编导。"
            "请基于给定的课程章节、核心概念、详细知识点和真实案例，生成一份教学微课分镜脚本。\n\n"
            "输出要求：\n"
            "1. 使用中文 Markdown。\n"
            "2. 必须生成包含时间、画面、旁白、屏幕文字的分镜脚本表格。\n"
            "3. 时间轴应覆盖一个 3 分钟左右的短视频或动画微课。\n"
            "4. 画面设计要能帮助学生理解抽象概念，旁白要准确、简洁、适合教学。\n"
            "5. 表格后可补充拍摄/制作提示和多模态工具交接参数。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        return self.use_llm_or_fallback(prompt, fallback)
