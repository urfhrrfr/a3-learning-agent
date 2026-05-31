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


class AnimationDemoAgent(ResourceAgent):
    name = "AnimationDemoAgent"
    resource_type = "animation_demo"
    content_format = "json"
    title_prefix = "可播放教学动画"
    stage = "producer"
    boundary = "生成可在前端直接播放的动态图解脚本，不导出 mp4 成片"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    allowed_templates = {"flow", "compare", "network", "search", "dialogue", "risk"}
    allowed_teaching_models = {
        "agent_loop",
        "ai_boundary_test",
        "search_pathfinding",
        "logic_rule_chain",
        "generalization_curve",
        "supervised_split",
        "cluster_space",
        "neural_training_loop",
        "language_pipeline",
        "vision_feature_map",
        "reinforcement_loop",
        "prompt_context_loop",
        "retrieval_tool_loop",
        "safety_case_review",
    }

    template_keywords = {
        "network": {"神经网络", "注意力", "知识图谱", "图", "连接", "权重", "节点"},
        "search": {"搜索", "路径", "规划", "强化学习", "状态", "智能体", "奖励", "策略"},
        "dialogue": {"提示词", "prompt", "对话", "问答", "自然语言", "生成", "聊天", "大模型", "语言模型", "大语言模型"},
        "compare": {"过拟合", "泛化", "监督", "无监督", "分类", "回归", "对比", "区别"},
        "risk": {"伦理", "偏见", "隐私", "安全", "公平", "风险", "幻觉", "可信"},
    }

    concept_model_map = {
        "智能体": "agent_loop",
        "应用场景": "agent_loop",
        "图灵测试": "ai_boundary_test",
        "弱人工智能": "ai_boundary_test",
        "状态空间": "search_pathfinding",
        "代价函数": "search_pathfinding",
        "A*": "search_pathfinding",
        "A*搜索": "search_pathfinding",
        "启发函数": "search_pathfinding",
        "命题逻辑": "logic_rule_chain",
        "谓词逻辑": "logic_rule_chain",
        "产生式规则": "logic_rule_chain",
        "本体": "logic_rule_chain",
        "训练集": "generalization_curve",
        "泛化": "generalization_curve",
        "损失函数": "generalization_curve",
        "过拟合": "generalization_curve",
        "分类": "supervised_split",
        "回归": "supervised_split",
        "决策树": "supervised_split",
        "评估指标": "supervised_split",
        "聚类": "cluster_space",
        "降维": "cluster_space",
        "K-means": "cluster_space",
        "主成分分析": "cluster_space",
        "感知机": "neural_training_loop",
        "反向传播": "neural_training_loop",
        "激活函数": "neural_training_loop",
        "梯度下降": "neural_training_loop",
        "注意力机制": "neural_training_loop",
        "Transformer自注意力": "neural_training_loop",
        "分词": "language_pipeline",
        "词向量": "language_pipeline",
        "序列建模": "language_pipeline",
        "文本分类": "language_pipeline",
        "图像特征": "vision_feature_map",
        "卷积": "vision_feature_map",
        "目标检测": "vision_feature_map",
        "数据增强": "vision_feature_map",
        "状态": "reinforcement_loop",
        "动作": "reinforcement_loop",
        "奖励": "reinforcement_loop",
        "策略": "reinforcement_loop",
        "强化学习": "reinforcement_loop",
        "上下文学习": "prompt_context_loop",
        "提示词": "prompt_context_loop",
        "RAG": "retrieval_tool_loop",
        "工具调用": "retrieval_tool_loop",
        "公平性": "safety_case_review",
        "隐私": "safety_case_review",
        "可解释性": "safety_case_review",
        "安全边界": "safety_case_review",
    }

    teaching_model_templates = {
        "agent_loop": "flow",
        "ai_boundary_test": "compare",
        "search_pathfinding": "search",
        "logic_rule_chain": "flow",
        "generalization_curve": "compare",
        "supervised_split": "compare",
        "cluster_space": "network",
        "neural_training_loop": "network",
        "language_pipeline": "dialogue",
        "vision_feature_map": "network",
        "reinforcement_loop": "search",
        "prompt_context_loop": "dialogue",
        "retrieval_tool_loop": "dialogue",
        "safety_case_review": "risk",
    }

    teaching_model_steps = {
        "agent_loop": [
            ("观察环境", "智能体先接收周围信息，弄清现在发生了什么。", "感知校园入口、任务提示和可用工具。", ["环境线索", "当前任务", "可选动作", "目标"], "把最终答案当成智能体本身。", "智能体先感知，再决定。"),
            ("做出决策", "它根据目标和规则选择下一步行动。", "比较可选动作，选出最符合目标的一步。", ["目标", "规则", "候选动作", "选择"], "以为智能体总是随机行动。", "行动来自目标和判断。"),
            ("执行行动", "选中的动作会改变环境或产生结果。", "把选择落到具体场景里，观察环境变化。", ["执行", "环境变化", "新结果", "记录"], "只看想法，不看行动后果。", "行动会带来新状态。"),
            ("继续循环", "新状态又会成为下一轮观察的起点。", "用结果开启下一轮观察和决策。", ["新状态", "反馈", "下一步", "循环"], "把智能体看成一次性流程。", "智能体是在循环里工作。"),
        ],
        "ai_boundary_test": [
            ("设置问题", "先给系统一个需要表现智能的任务。", "把问题、回答者和判断标准摆出来。", ["任务", "回答者", "观察者", "标准"], "只看名字判断智能。", "测试要有明确标准。"),
            ("观察表现", "看它是否能给出像样的行为或回答。", "比较系统表现和人的表现差异。", ["系统表现", "人类表现", "相似点", "差异"], "把会聊天等同于真理解。", "像不像不等于全都会。"),
            ("划清边界", "判断它在哪些任务上有效，哪些任务上不行。", "把可用能力和不能做的事分开。", ["能做", "不能做", "任务边界", "证据"], "把单项能力夸成通用智能。", "智能有范围。"),
            ("迁移判断", "换一个任务再检查它是否仍然可靠。", "用新场景验证边界有没有改变。", ["新任务", "新证据", "边界修正", "结论"], "一次通过就认为永远可靠。", "换场景要重新判断。"),
        ],
        "search_pathfinding": [
            ("确定状态", "先把问题拆成一个个可能位置或局面。", "标出起点、目标和可走的状态。", ["起点", "状态空间", "目标", "障碍"], "直接猜答案，不列出状态。", "先看有哪些状态。"),
            ("计算选择", "比较不同路径的代价和启发信息。", "给候选路线标出代价和估计距离。", ["候选路径", "代价", "启发值", "优先级"], "只看离目标近，不看总代价。", "路径好坏要同时看代价和估计。"),
            ("扩展路径", "每次优先探索看起来最有希望的路线。", "让高优先级路径变亮并向前延伸。", ["当前节点", "邻居", "开放表", "已检查"], "重复走已经检查过的路。", "搜索要有顺序地试。"),
            ("得到路线", "当目标被找到，就回溯出可执行路径。", "把最终路径连成清楚的一条线。", ["目标", "最优路径", "总代价", "结果"], "找到一条路就以为一定最好。", "好搜索能解释为什么选这条路。"),
        ],
        "logic_rule_chain": [
            ("写出事实", "先把已知条件写成清楚的事实。", "把生活描述变成可判断的条件。", ["事实A", "事实B", "对象", "条件"], "条件含糊会让推理失真。", "推理从清楚事实开始。"),
            ("匹配规则", "再找哪些规则能被这些事实触发。", "让满足条件的规则亮起来。", ["如果", "那么", "匹配", "触发"], "把没有满足条件的规则也拿来用。", "规则要先匹配条件。"),
            ("推出结论", "被触发的规则会生成新的结论。", "把新结论接到推理链后面。", ["中间结论", "新事实", "链条", "证明"], "跳过中间步骤直接下结论。", "结论要能追溯。"),
            ("检查冲突", "最后检查有没有互相矛盾或缺证据的地方。", "用证据链确认结论是否站得住。", ["冲突", "缺口", "证据", "修正"], "只要形式像规则就相信。", "推理也要检查。"),
        ],
        "generalization_curve": [
            ("准备样本", "先用训练集学习规律，同时留出新样本检验。", "把旧题和新题分开摆放。", ["训练集", "验证集", "样本", "目标"], "把训练题当成全部世界。", "学习要留新题检查。"),
            ("观察损失", "训练时损失下降，说明旧样本越来越会做。", "让训练曲线下降并显示误差变小。", ["训练损失", "模型", "旧题表现", "下降"], "只看训练集变好。", "旧题好不代表真会。"),
            ("检查泛化", "如果新样本表现变差，就可能记住了噪声。", "让验证曲线抬头，标出过拟合风险。", ["新样本", "验证损失", "噪声", "风险"], "把背题当成理解。", "新题表现才检验泛化。"),
            ("调整模型", "通过简化模型、增加数据或正则化改善表现。", "让两条曲线重新靠近。", ["简化", "更多数据", "正则化", "泛化"], "继续加复杂度解决一切。", "好模型要能做新题。"),
        ],
        "supervised_split": [
            ("准备标签", "监督学习先要有输入和正确答案。", "把样本和标签配成一对。", ["样本", "标签", "特征", "答案"], "没有标签也当监督学习。", "监督学习靠答案示范。"),
            ("学习边界", "模型从样本里找出判断规律。", "用边界、树枝或函数把样本分开。", ["规律", "边界", "分支", "预测"], "只记单个样本，不学规律。", "模型学的是可迁移规律。"),
            ("预测新例", "遇到新样本时，根据学到的规律给出预测。", "把新点放进模型并显示预测结果。", ["新样本", "预测", "类别/数值", "置信度"], "把预测当成绝对正确。", "预测需要被检验。"),
            ("评价效果", "最后用指标看预测到底好不好。", "显示准确率、误差或召回等指标。", ["指标", "错误样本", "改进方向", "结果"], "只看一个漂亮分数。", "指标要服务任务目标。"),
        ],
        "cluster_space": [
            ("摆出数据", "无监督学习先看到很多没有标签的数据点。", "把数据点放到空间里。", ["数据点", "特征空间", "距离", "形状"], "以为没有标签就不能分析。", "无标签也能找结构。"),
            ("寻找结构", "相似的数据会在空间里靠得更近。", "让近的点逐渐聚成组。", ["相似", "距离", "簇", "中心"], "只凭颜色或名字分组。", "分组看数据关系。"),
            ("压缩表示", "降维会保留主要变化方向，方便观察。", "把高维信息投影到更容易看的平面。", ["主方向", "投影", "保留信息", "压缩"], "降维等于没有损失。", "降维是保留重点。"),
            ("解释分组", "最后要解释每一组可能代表什么。", "给簇贴上可解释的含义。", ["群组", "特征", "解释", "应用"], "聚出来就直接当真理。", "聚类结果需要解释。"),
        ],
        "neural_training_loop": [
            ("输入信号", "神经网络先把输入拆成可计算的信号。", "让特征进入节点并形成连接。", ["输入", "节点", "连接", "信号"], "把网络看成黑箱魔法。", "网络从信号开始计算。"),
            ("加权激活", "连接有权重，节点会决定信号是否继续传递。", "重要连接变亮，弱连接变淡。", ["权重", "激活", "重要信号", "输出"], "每个输入都同样重要。", "权重表示影响大小。"),
            ("看到误差", "输出和答案不同，就会产生误差信号。", "把误差从结果端标出来。", ["预测", "答案", "误差", "损失"], "错了只改最终答案。", "误差告诉哪里要调整。"),
            ("更新参数", "训练会沿着能降低误差的方向调整权重。", "让权重和连接逐步变化。", ["梯度", "更新", "权重", "更小误差"], "一次更新就完全学会。", "训练是多轮小步调整。"),
        ],
        "language_pipeline": [
            ("切开文本", "先把一句话切成模型能处理的小单元。", "把句子拆成词或片段。", ["句子", "词", "片段", "位置"], "把整段文字当成一个不可拆的块。", "文本要先变成单元。"),
            ("变成向量", "每个词会变成带有语义位置的数字表示。", "让词卡片进入语义空间。", ["词向量", "语义", "位置", "相似度"], "以为向量只是编号。", "向量保存语义线索。"),
            ("理解顺序", "序列模型会看前后关系，判断当前词的含义。", "让上下文线索连到关键词。", ["上下文", "顺序", "关系", "含义"], "只看单词不看上下文。", "语境会改变含义。"),
            ("完成任务", "最后把理解结果用于分类、抽取或生成。", "显示文本类别或输出结果。", ["任务", "类别", "结果", "检查"], "把文本处理只当翻译。", "语言处理服务具体任务。"),
        ],
        "vision_feature_map": [
            ("读取图像", "计算机先把图像看成像素和局部区域。", "把图片切成小块和像素格。", ["像素", "局部区域", "颜色", "边缘"], "以为模型直接看懂整张图。", "视觉从局部特征开始。"),
            ("提取特征", "卷积或特征方法会找边缘、纹理和形状。", "让特征窗口扫过图片。", ["卷积核", "边缘", "纹理", "形状"], "只看一个像素做判断。", "局部特征组合成线索。"),
            ("定位目标", "模型把多个特征合起来判断目标在哪里。", "给目标框加亮并显示类别。", ["目标框", "类别", "置信度", "位置"], "看见相似纹理就一定是目标。", "识别要结合位置和整体。"),
            ("增强鲁棒", "通过旋转、裁剪等增强让模型见过更多变化。", "显示同一图像的多种变化。", ["旋转", "裁剪", "光照", "鲁棒"], "只在原图上表现好就够了。", "变化训练帮助适应新图。"),
        ],
        "reinforcement_loop": [
            ("观察状态", "智能体先观察自己现在处在哪个状态。", "在环境格子里高亮当前位置和目标。", ["当前状态", "环境", "目标", "可选动作"], "一上来就背策略，不看当前局面。", "先看状态，再谈选择。"),
            ("选择动作", "它从可选动作里尝试走一步。", "让动作箭头指向本轮选择。", ["向左", "向右", "尝试动作", "下一格"], "以为动作一定一开始就最优。", "动作是一次选择。"),
            ("获得奖励", "环境会用奖励或惩罚告诉这一步好不好。", "弹出 +1 或 -1，并显示离目标更近或更远。", ["奖励 +1", "惩罚 -1", "环境反馈", "结果"], "只看是否移动，不看反馈。", "奖励告诉方向对不对。"),
            ("更新策略", "智能体根据反馈调整下次更倾向的动作。", "让更好的策略箭头变粗变亮。", ["策略", "更新", "更好选择", "下一轮"], "把一次奖励当成固定答案。", "策略来自反复试错。"),
        ],
        "prompt_context_loop": [
            ("提出任务", "先把想让模型做什么说清楚。", "把任务目标和限制写进提示词。", ["任务", "要求", "限制", "输出格式"], "提示词只写一句模糊愿望。", "说清任务，回答才稳。"),
            ("补充上下文", "上下文会告诉模型应该按什么背景理解。", "把材料、角色和前文接到问题旁边。", ["背景", "材料", "角色", "前文"], "忽略上下文变化。", "上下文会改变回答。"),
            ("生成回答", "模型根据任务和上下文组织输出。", "让答案从提示和上下文中汇合生成。", ["线索", "组织", "回答", "格式"], "以为生成就是复制。", "回答是按条件组织出来的。"),
            ("检查改写", "最后看回答是否满足目标，不满足就改提示。", "标出缺口并回到提示词修改。", ["检查", "缺口", "改写", "更好回答"], "第一版回答不改就用。", "好提示来自迭代。"),
        ],
        "retrieval_tool_loop": [
            ("提出问题", "先明确问题需要哪些外部资料或工具。", "把问题拆成需要查证的线索。", ["问题", "关键词", "资料需求", "工具需求"], "让模型凭空回答所有事实。", "先判断需不需要外部信息。"),
            ("检索/调用", "系统去资料库检索，或调用工具获得结果。", "让资料卡片或工具结果进入工作区。", ["检索", "工具", "资料片段", "返回结果"], "检索到什么都直接相信。", "外部信息要看来源。"),
            ("结合证据", "回答要把问题和证据放在一起组织。", "把证据连到最终回答。", ["证据", "引用", "整合", "回答"], "只贴资料，不回答问题。", "RAG 要用证据回答。"),
            ("核对边界", "最后检查有没有缺资料、过期或不确定。", "给答案加上来源和不确定提示。", ["来源", "缺口", "不确定", "边界"], "有检索就一定正确。", "检索增强也要核对。"),
        ],
        "safety_case_review": [
            ("看真实场景", "先把风险放回具体使用场景里。", "展示谁会受到影响、系统做了什么。", ["使用者", "场景", "系统行为", "影响"], "只背原则不看场景。", "风险来自具体使用。"),
            ("识别信号", "找出偏见、隐私泄露或不可解释等风险信号。", "让风险信号逐个亮起。", ["偏见", "隐私", "解释缺口", "安全风险"], "结果看起来有用就忽略风险。", "先识别风险信号。"),
            ("评估影响", "判断风险会影响谁、影响多大。", "把受影响对象和后果连起来。", ["影响对象", "后果", "严重度", "证据"], "只看平均效果。", "安全要看具体影响。"),
            ("加上护栏", "用规则、审核和解释降低风险。", "给系统加上检查点和人工复核。", ["规则", "审核", "解释", "人工复核"], "只靠模型自觉。", "护栏让应用更可信。"),
        ],
    }

    def _all_course_concepts(self, state: WorkflowState) -> list[str]:
        concepts = [str(item) for item in state.chapter.get("concepts", []) if str(item).strip()]
        for item in state.profile.weak_points:
            if item not in concepts:
                concepts.append(item)
        return concepts

    def _select_concept(self, state: WorkflowState) -> str:
        text = " ".join([state.request.goal, *map(str, state.profile.weak_points), state.chapter["title"]]).lower()
        candidates = self._all_course_concepts(state)
        for concept in candidates:
            if concept.lower() in text:
                return concept
        for concept in candidates:
            if concept in self.concept_model_map:
                return concept
        return candidates[0] if candidates else state.chapter["title"]

    def _teaching_model_for_concept(self, concept: str, state: WorkflowState) -> str:
        text = f"{concept} {state.chapter['title']} {state.request.goal} {' '.join(map(str, state.profile.weak_points))}".lower()
        for key, model in self.concept_model_map.items():
            if key.lower() in text:
                return model
        return "agent_loop"

    def _legacy_template_for_model(self, teaching_model_id: str) -> str:
        return self.teaching_model_templates.get(teaching_model_id, "flow")

    def _animation_template(self, state: WorkflowState) -> str:
        concept = self._select_concept(state)
        teaching_model_id = self._teaching_model_for_concept(concept, state)
        if teaching_model_id:
            return self._legacy_template_for_model(teaching_model_id)
        text = " ".join([state.chapter["title"], *map(str, state.chapter.get("concepts", [])), *map(str, state.profile.weak_points), state.request.goal]).lower()
        for template, keywords in self.template_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                return template
        return "flow"

    def _visual_for_template(self, template: str, index: int) -> str:
        visuals = {
            "flow": ["flow_input", "flow_process", "flow_feedback", "flow_check"],
            "compare": ["compare_left", "compare_right", "compare_gap", "compare_fix"],
            "network": ["network_nodes", "network_signal", "network_weight", "network_output"],
            "search": ["search_start", "search_try", "search_reward", "search_path"],
            "dialogue": ["dialogue_prompt", "dialogue_context", "dialogue_reason", "dialogue_answer"],
            "risk": ["risk_case", "risk_signal", "risk_choice", "risk_guardrail"],
        }
        return visuals.get(template, visuals["flow"])[index]

    def _fallback_frame(self, teaching_model_id: str, concept: str, index: int) -> dict:
        steps = self.teaching_model_steps.get(teaching_model_id, self.teaching_model_steps["agent_loop"])
        title, caption, action, scene_objects, misconception, takeaway = steps[index]
        template = self._legacy_template_for_model(teaching_model_id)
        return {
            "id": f"frame_{index + 1:02d}",
            "title": title,
            "caption": caption.replace("这个知识点", concept),
            "focus": concept,
            "visual": self._visual_for_template(template, index),
            "scene_objects": scene_objects,
            "metric": title,
            "action": action,
            "misconception": misconception,
            "takeaway": takeaway,
        }

    def _sanitize_html_document(self, html: str) -> str:
        html = str(html or "").strip()
        if not html:
            return ""
        html = re.sub(r"<\s*script[\s\S]*?<\s*/\s*script\s*>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*(['\"])[\s\S]*?\1", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*[^\s>]+", "", html, flags=re.IGNORECASE)
        html = re.sub(r"javascript\s*:", "", html, flags=re.IGNORECASE)
        if "<html" not in html.lower():
            html = f"<!doctype html><html><head><meta charset=\"utf-8\"></head><body>{html}</body></html>"
        if "<meta charset" not in html.lower():
            html = html.replace("<head>", "<head><meta charset=\"utf-8\">", 1)
        return html[:60000]

    def _html_document_from_payload(self, payload: dict) -> str:
        frames = payload.get("frames") if isinstance(payload.get("frames"), list) else []
        concept = escape(str(payload.get("concept") or payload.get("topic") or "Animation"))
        topic = escape(str(payload.get("topic") or concept))
        scenario = escape(str(payload.get("scenario") or topic))
        note = escape(str(payload.get("playback_note") or ""))
        frame_cards = []
        for index, frame in enumerate(frames[:4], start=1):
            title = escape(str(frame.get("title") or f"Step {index}"))
            caption = escape(str(frame.get("caption") or ""))
            action = escape(str(frame.get("action") or ""))
            takeaway = escape(str(frame.get("takeaway") or ""))
            objects = frame.get("scene_objects") if isinstance(frame.get("scene_objects"), list) else []
            object_tags = "".join(f"<span>{escape(str(item))}</span>" for item in objects[:4])
            frame_cards.append(
                f"""
        <article class="scene scene-{index}">
          <div class="scene-index">0{index}</div>
          <div class="scene-copy">
            <h2>{title}</h2>
            <p>{caption}</p>
            <small>{action}</small>
          </div>
          <div class="scene-objects">{object_tags}</div>
          <strong>{takeaway}</strong>
        </article>"""
            )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{concept} 教学动画</title>
  <style>
    :root {{ color-scheme: light; --ink:#173248; --paper:#fbf8ef; --teal:#176c7a; --gold:#d69b2d; --coral:#d95f43; --blue:#315f9b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: var(--ink); background: var(--paper); overflow: hidden; }}
    .stage {{ position: relative; min-height: 100vh; padding: 34px; background:
      linear-gradient(90deg, rgba(23,108,122,.09) 1px, transparent 1px),
      linear-gradient(0deg, rgba(23,108,122,.08) 1px, transparent 1px),
      radial-gradient(circle at 78% 18%, rgba(217,95,67,.20), transparent 28%),
      radial-gradient(circle at 16% 78%, rgba(49,95,155,.18), transparent 30%),
      var(--paper); background-size: 34px 34px, 34px 34px, auto, auto; }}
    header {{ position: relative; z-index: 3; max-width: 760px; }}
    .eyebrow {{ margin: 0 0 8px; color: var(--teal); font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ margin: 0; font-size: clamp(28px, 5vw, 54px); line-height: 1.02; letter-spacing: 0; }}
    header p {{ max-width: 620px; margin: 12px 0 0; color: #42586b; font-size: 16px; line-height: 1.7; }}
    .scenario {{ position: absolute; right: 34px; top: 34px; max-width: 280px; padding: 12px 14px; border-left: 4px solid var(--gold); background: rgba(255,255,255,.78); font-size: 13px; line-height: 1.55; z-index: 4; }}
    .track {{ position: absolute; inset: 170px 34px 34px; display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 14px; align-items: stretch; }}
    .scene {{ position: relative; display: grid; grid-template-rows: auto 1fr auto auto; gap: 12px; min-width: 0; padding: 18px; border: 1px solid rgba(23,50,72,.16); background: rgba(255,255,255,.78); box-shadow: 0 18px 42px rgba(23,50,72,.10); animation: rise 12.8s ease-in-out infinite; animation-delay: calc((var(--i) - 1) * 3.2s); }}
    .scene-1 {{ --i: 1; }} .scene-2 {{ --i: 2; }} .scene-3 {{ --i: 3; }} .scene-4 {{ --i: 4; }}
    .scene-index {{ display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; background: var(--ink); color: #fff; font-weight: 900; }}
    .scene h2 {{ margin: 0; font-size: 20px; line-height: 1.2; }}
    .scene p {{ margin: 8px 0 0; color: #42586b; font-size: 14px; line-height: 1.65; }}
    .scene small {{ display: block; margin-top: 10px; color: var(--teal); font-weight: 800; line-height: 1.45; }}
    .scene-objects {{ display: grid; gap: 8px; }}
    .scene-objects span {{ padding: 9px 10px; border: 1px solid rgba(23,108,122,.18); background: #eef8fb; color: #174f3d; font-size: 13px; font-weight: 900; text-align: center; }}
    .scene strong {{ color: #714b08; line-height: 1.45; }}
    .beam {{ position: absolute; left: 8%; right: 8%; top: 56%; height: 5px; border-radius: 999px; background: linear-gradient(90deg, var(--teal), var(--gold), var(--coral), var(--blue)); animation: pulse 3.2s ease-in-out infinite; }}
    @keyframes rise {{ 0%, 18%, 100% {{ transform: translateY(0) scale(1); filter: saturate(.92); }} 7%, 12% {{ transform: translateY(-16px) scale(1.025); filter: saturate(1.15); }} }}
    @keyframes pulse {{ 0%, 100% {{ transform: scaleX(.72); opacity: .35; }} 50% {{ transform: scaleX(1); opacity: .9; }} }}
    @media (max-width: 780px) {{ body {{ overflow: auto; }} .stage {{ min-height: auto; padding: 20px; }} .scenario {{ position: static; margin-top: 14px; max-width: none; }} .track {{ position: static; margin-top: 20px; grid-template-columns: 1fr; }} .beam {{ display: none; }} }}
  </style>
</head>
<body>
  <main class="stage">
    <header>
      <p class="eyebrow">HTML animation lesson</p>
      <h1>{concept}</h1>
      <p>{note}</p>
    </header>
    <aside class="scenario">{scenario}</aside>
    <div class="beam" aria-hidden="true"></div>
    <section class="track" aria-label="{concept} 四幕教学动画">
      {"".join(frame_cards)}
    </section>
  </main>
</body>
</html>"""

    def _normalize_animation_payload(self, parsed: dict, state: WorkflowState, fallback: str) -> dict:
        fallback_payload = json.loads(fallback)
        selected_concept = str(parsed.get("concept") or fallback_payload.get("concept") or self._select_concept(state))
        teaching_model_id = str(parsed.get("teaching_model_id") or fallback_payload.get("teaching_model_id") or "").strip()
        if teaching_model_id not in self.allowed_teaching_models:
            teaching_model_id = self._teaching_model_for_concept(selected_concept, state)

        template = str(parsed.get("template") or fallback_payload.get("template") or "").strip().lower()
        if template not in self.allowed_templates:
            template = self._legacy_template_for_model(teaching_model_id)

        fallback_frames = fallback_payload.get("frames", [])
        raw_frames = parsed.get("frames") if isinstance(parsed.get("frames"), list) else []
        frames = []
        for index in range(4):
            raw = raw_frames[index] if index < len(raw_frames) and isinstance(raw_frames[index], dict) else {}
            base = fallback_frames[index] if index < len(fallback_frames) and isinstance(fallback_frames[index], dict) else {}
            scene_objects = raw.get("scene_objects")
            if not isinstance(scene_objects, list) or len(scene_objects) < 4:
                scene_objects = base.get("scene_objects", ["输入信息", "处理过程", "输出结果", "检查效果"])
            frames.append(
                {
                    "id": str(raw.get("id") or base.get("id") or f"frame_{index + 1:02d}"),
                    "title": str(raw.get("title") or base.get("title") or f"第 {index + 1} 幕"),
                    "caption": str(raw.get("caption") or base.get("caption") or "用一个简单场景解释这个知识点。"),
                    "focus": str(raw.get("focus") or base.get("focus") or state.chapter["title"]),
                    "visual": str(raw.get("visual") or self._visual_for_template(template, index)),
                    "scene_objects": [str(item) for item in scene_objects[:4]],
                    "metric": str(raw.get("metric") or base.get("metric") or "观察重点"),
                    "action": str(raw.get("action") or base.get("action") or "观察画面里的变化。"),
                    "misconception": str(raw.get("misconception") or base.get("misconception") or "不要只背名词，要看过程。"),
                    "takeaway": str(raw.get("takeaway") or base.get("takeaway") or "先看懂场景，再记住概念。"),
                }
            )

        payload = {
            "schema_version": 2,
            "kind": "in_app_animation",
            "teaching_model_id": teaching_model_id,
            "template": template,
            "concept": selected_concept,
            "topic": str(parsed.get("topic") or fallback_payload.get("topic") or state.chapter["title"]),
            "duration_seconds": int(parsed.get("duration_seconds") or fallback_payload.get("duration_seconds") or 60),
            "playback_note": str(
                parsed.get("playback_note")
                or fallback_payload.get("playback_note")
                or "这是系统内可播放的初学者动画小课。"
            ),
            "scenario": str(parsed.get("scenario") or fallback_payload.get("scenario") or state.chapter["title"]),
            "frames": frames,
            "teacher_prompt": str(
                parsed.get("teacher_prompt")
                or fallback_payload.get("teacher_prompt")
                or "播放时用生活化语言解释每一幕。"
            ),
        }

        html_document = self._sanitize_html_document(str(parsed.get("html_document") or ""))
        payload["html_document"] = html_document or self._html_document_from_payload(payload)
        return payload

    def content(self, state: WorkflowState) -> str:
        cases = state.chapter["real_cases"]
        concept = self._select_concept(state)
        teaching_model_id = self._teaching_model_for_concept(concept, state)
        template = self._legacy_template_for_model(teaching_model_id)
        frames = [self._fallback_frame(teaching_model_id, concept, index) for index in range(4)]
        payload = {
                "schema_version": 2,
                "kind": "in_app_animation",
                "teaching_model_id": teaching_model_id,
                "template": template,
                "concept": concept,
                "topic": state.chapter["title"],
                "duration_seconds": 60,
                "playback_note": f"本动画用“{concept}”的专属教学模型演示核心过程，适合课堂上自动循环播放，每幕停留约15秒。",
                "scenario": cases[0] if cases else state.chapter["title"],
                "frames": frames,
                "teacher_prompt": f"播放时抓住“{concept}”的过程变化：先看当前局面，再看关键动作、反馈和修正。不要只让学生背定义。",
            }
        payload["html_document"] = self._html_document_from_payload(payload)
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个教学动画导演和计算机课程教师。请生成一个可在网页前端直接播放的教学动画 JSON，"
            "用于把人工智能导论中的任意知识点转成初学者能看懂的动态小课。\n\n"
            "只输出 JSON，不要输出 Markdown，不要包裹代码块。\n"
            "JSON 必须包含 schema_version、kind、teaching_model_id、template、concept、topic、duration_seconds、playback_note、scenario、frames、teacher_prompt。\n"
            f"teaching_model_id 必须使用：{self._teaching_model_for_concept(self._select_concept(state), state)}。\n"
            "template 只能从 flow、compare、network、search、dialogue、risk 中选择。\n"
            "frames 必须刚好 4 幕，不要多也不要少。\n"
            "frames 是数组，每项必须包含 id、title、caption、focus、visual、scene_objects、metric、action、misconception、takeaway。"
            "scene_objects 是 4 个可显示在画面里的中文短标签，必须生活化、可视化，避免堆术语，例如“历史选课记录”“新同学画像”“推荐课程”“是否满意”。"
            "metric 是当前场景要观察的指标短语，takeaway 是一句初学者能记住的结论。"
            "caption、takeaway 必须用初中生也能听懂的中文，不要写教材式长段落。\n\n"
            "禁止把所有知识点都写成“输入 → AI处理 → 输出”。除非知识点本身是大模型、提示词、RAG 或工具调用，"
            "不要写“先把问题交给 AI”“AI 会一步步处理信息”这类泛化话术。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"学生画像：专业={state.profile.major}，薄弱点={state.profile.weak_points}，偏好={state.profile.preferred_modalities}，目标={state.request.goal}\n"
        )
        content, used_llm, reason = self.use_llm_or_fallback(prompt, fallback)
        if used_llm:
            try:
                parsed = parse_llm_json(content)
                frames = parsed.get("frames") if isinstance(parsed, dict) else None
                if isinstance(frames, list) and frames:
                    normalized = self._normalize_animation_payload(parsed, state, fallback)
                    return json.dumps(normalized, ensure_ascii=False, indent=2), True, ""
                return fallback, False, "LLM returned animation JSON without frames"
            except json.JSONDecodeError as exc:
                return fallback, False, f"LLM returned invalid animation JSON: {exc}"
        return content, used_llm, reason

    def _html_animation_prompt(self, state: WorkflowState, teaching_model_id: str, concept: str) -> str:
        template = self._legacy_template_for_model(teaching_model_id)
        return (
            "你是资深前端动画设计师、计算机课程教师和教学可视化导演。\n"
            "请直接生成一份完整、可运行的 HTML 教学动画页面，用来嵌入 iframe srcdoc 预览。\n\n"
            "输出要求：\n"
            "1. 只输出 HTML 文档本身，从 <!doctype html> 或 <html> 开始，不要 Markdown，不要解释文字。\n"
            "2. 必须把 CSS 写在 <style> 里，可以使用 CSS keyframes、SVG、纯 HTML 元素；不要使用外链资源。\n"
            "3. 不要写 <script>、onclick 等事件属性、网络请求、表单提交、iframe 或外部字体。\n"
            "4. 画面要像一个真正的动态教学小课，不要只是四个静态卡片并排。\n"
            "5. 至少包含 3 个连续动画阶段：概念进入、过程变化、误区纠正/结果验证。\n"
            "6. 用中文短句标注关键对象，避免教材长段落；动画应能自动循环。\n"
            "7. 视觉要服务当前知识点，不要套用通用“输入 -> AI处理 -> 输出”。\n"
            "8. 所有文字必须清晰可读：底部说明、徽章、阶段提示和旁白必须使用独立块级区域或 flex-wrap，可自动换行；不要把多段文字绝对定位在同一条底部横线上；不要让文字互相覆盖、截断或压在图形上。\n"
            "9. 整体画面保持紧凑的 16:9 教学舞台，内容应在 1280x720 级别清晰显示；不要生成超大卡片、超大留白、超长页面或需要大幅滚动才能看懂的布局。\n"
            "10. 标题建议 24-42px，正文/标签建议 14-18px；每个文字区只表达一个信息点，使用短句、分组和留白来提升可读性。\n"
            "11. 如果教学模型是 retrieval_tool_loop 或主题包含 RAG/检索增强生成，必须用紧凑一屏展示“问题 -> 检索 -> 证据/引用 -> 回答 -> 边界核对”，保留标题和流程说明，不要用迷宫、巨大装饰图或超大空白。\n"
            "12. 如果教学模型是 reinforcement_loop 或 search_pathfinding，必须以迷宫/路径/状态-动作-奖励为主画面，顶部装饰必须很小，不能挤掉网格和状态说明。\n"
            "13. 所有 HTML 动画都不要依赖 iframe 内部滚动条；核心内容必须在 16:9 舞台内完整可见。\n"
            "14. 画面高度不足时应优先缩小图形、分栏或减少装饰，而不是让内容溢出；任何说明文字区域都要设置合理 line-height、gap、min-height 和 padding。\n"
            "15. 兼容旧解析：如果你选择返回 JSON，frames 必须刚好 4 幕，但本次优先返回完整 HTML。\n\n"
            f"知识点：{concept}\n"
            f"教学模型：{teaching_model_id}\n"
            f"建议视觉类型：{template}\n"
            f"章节：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"学生画像：专业={state.profile.major}，薄弱点={state.profile.weak_points}，偏好={state.profile.preferred_modalities}，目标={state.request.goal}\n"
        )

    def _extract_html_document(self, content: str) -> str:
        text = str(content or "").strip()
        fence = re.search(r"```(?:html)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        if "<html" in text.lower() or "<!doctype" in text.lower() or "<body" in text.lower():
            return self._sanitize_html_document(text)
        try:
            parsed = parse_llm_json(text)
        except json.JSONDecodeError:
            return ""
        if isinstance(parsed, dict):
            return self._sanitize_html_document(str(parsed.get("html_document") or parsed.get("html") or ""))
        return ""

    def _payload_with_html_document(self, html: str, state: WorkflowState, fallback: str) -> dict:
        payload = json.loads(fallback)
        payload["kind"] = "html_animation"
        payload["topic"] = state.chapter["title"]
        payload["playback_note"] = "由 HTML 动画提示词生成，可在页面内直接预览。"
        payload["html_document"] = self._sanitize_html_document(html) or self._html_document_from_payload(payload)
        return payload

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        concept = self._select_concept(state)
        teaching_model_id = self._teaching_model_for_concept(concept, state)
        prompt = self._html_animation_prompt(state, teaching_model_id, concept)
        content, used_llm, reason = self.use_llm_or_fallback(prompt, fallback)
        if used_llm:
            html_document = self._extract_html_document(content)
            if html_document:
                payload = self._payload_with_html_document(html_document, state, fallback)
                return json.dumps(payload, ensure_ascii=False, indent=2), True, ""
            try:
                parsed = parse_llm_json(content)
                frames = parsed.get("frames") if isinstance(parsed, dict) else None
                if isinstance(frames, list) and frames:
                    normalized = self._normalize_animation_payload(parsed, state, fallback)
                    return json.dumps(normalized, ensure_ascii=False, indent=2), True, ""
                return fallback, False, "LLM returned neither HTML nor animation frames"
            except json.JSONDecodeError as exc:
                return fallback, False, f"LLM returned invalid animation HTML/JSON: {exc}"
        return content, used_llm, reason
