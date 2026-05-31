from __future__ import annotations

import re
from pathlib import Path


CHAPTER_BLUEPRINTS = [
    ("人工智能概述", ["智能体", "图灵测试", "弱人工智能", "应用场景"]),
    ("搜索问题与启发式搜索", ["状态空间", "代价函数", "A*", "启发函数"]),
    ("知识表示与推理", ["命题逻辑", "谓词逻辑", "产生式规则", "本体"]),
    ("机器学习基础", ["训练集", "泛化", "损失函数", "过拟合"]),
    ("监督学习", ["分类", "回归", "决策树", "评估指标"]),
    ("无监督学习", ["聚类", "降维", "K-means", "主成分分析"]),
    ("神经网络与深度学习入门", ["感知机", "反向传播", "激活函数", "梯度下降"]),
    ("自然语言处理基础", ["分词", "词向量", "序列建模", "文本分类"]),
    ("计算机视觉基础", ["图像特征", "卷积", "目标检测", "数据增强"]),
    ("强化学习基础", ["状态", "动作", "奖励", "策略"]),
    ("大模型与提示词工程", ["上下文学习", "提示词", "RAG", "工具调用"]),
    ("AI 伦理、安全与应用实践", ["公平性", "隐私", "可解释性", "安全边界"]),
]

COURSE_KB_PATH = Path(__file__).resolve().parents[1] / "data" / "courses" / "ai_intro" / "knowledge-base.md"

FIELD_NAMES = {
    "所属模块",
    "核心解释",
    "基本原理",
    "典型例子",
    "适用场景",
    "优点",
    "局限",
    "关键概念",
    "关键参数",
    "关键模块",
    "完整流程",
    "缓解方法",
    "关键词",
    "常见问法",
}


def clean_title(title: str) -> str:
    return re.sub(r"\s*[（(].*?[）)]\s*", "", title).strip()


def strip_module_number(title: str) -> str:
    return re.sub(r"^\d+\s+", "", title).strip()


def split_keywords(value: str) -> list[str]:
    raw = re.split(r"[、,，;；]\s*", value)
    return [item.strip() for item in raw if item.strip()]


def normalize_field_value(values: list[str] | str | None) -> str:
    if values is None:
        return ""
    if isinstance(values, str):
        return values.strip()
    return "；".join(value.strip(" -") for value in values if value.strip(" -")).strip()


def parse_knowledge_markdown(path: Path = COURSE_KB_PATH) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)

    modules: list[dict] = []
    current_module: dict | None = None
    current_point: dict | None = None
    current_field: str | None = None

    def finish_point() -> None:
        nonlocal current_point, current_module, current_field
        if current_module is not None and current_point is not None:
            current_module["points"].append(current_point)
        current_point = None
        current_field = None

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        module_match = re.match(r"^##\s+(.+)$", line)
        if module_match:
            finish_point()
            module_title = strip_module_number(module_match.group(1))
            current_module = {"title": module_title, "points": []}
            modules.append(current_module)
            continue

        point_match = re.match(r"^###\s+标题：(.+)$", line)
        if point_match:
            finish_point()
            if current_module is None:
                continue
            current_point = {"title": point_match.group(1).strip(), "fields": {}}
            continue

        if current_point is None:
            continue

        field_match = re.match(r"^([^：:]{2,20})[：:](.*)$", line)
        if field_match and field_match.group(1).strip() in FIELD_NAMES:
            current_field = field_match.group(1).strip()
            value = field_match.group(2).strip()
            current_point["fields"].setdefault(current_field, [])
            if value:
                current_point["fields"][current_field].append(value)
            continue

        if current_field:
            current_point["fields"].setdefault(current_field, [])
            current_point["fields"][current_field].append(line)

    finish_point()
    modules = [module for module in modules if module["points"]]
    if not modules:
        raise ValueError("knowledge-base.md does not contain parseable modules")
    return modules


def build_question(chapter_id: str, title: str, concepts: list[str], index: int) -> dict:
    concept = concepts[(index - 1) % len(concepts)]
    question_id = f"{chapter_id}#q{index:02d}"
    if index == 1:
        return {
            "id": question_id,
            "type": "choice",
            "stem": f"在“{title}”中，下列哪一项最能体现“{concept}”的作用？",
            "standard_answer": "应选择能同时描述概念含义、适用条件与任务影响的选项。",
            "explanation": f"{concept} 不是孤立术语，需要放回任务目标、输入输出和应用限制中理解。",
            "difficulty": "基础",
            "assessment_point": f"{concept} 的概念识别与任务映射",
            "options": ["只背术语名称", "同时说明概念含义、适用条件与任务影响", "只关注最终分数", "直接套用其他章节结论"],
            "rubric": ["能解释概念含义", "能说明适用条件", "能联系任务影响"],
        }
    if index == 2:
        return {
            "id": question_id,
            "type": "true_false",
            "stem": f"判断：只要能复述“{concept}”的定义，就说明已经掌握“{title}”。",
            "standard_answer": "错误",
            "explanation": "课程答疑更关注能否解释原理、举例、比较相近概念并迁移到新场景。",
            "difficulty": "基础",
            "assessment_point": f"{concept} 的理解深度",
            "options": ["正确", "错误"],
            "rubric": ["能识别定义复述的局限", "能补充原理或应用说明"],
        }
    if index == 3:
        return {
            "id": question_id,
            "type": "short_answer",
            "stem": f"简答：请用 3 句话解释“{concept}”并给出一个实际例子。",
            "standard_answer": "应包含核心定义、基本原理和一个贴近课程或真实场景的例子。",
            "explanation": "能把定义、原理和例子连起来，说明学习者可以从记忆走向理解。",
            "difficulty": "应用",
            "assessment_point": f"{concept} 的解释与举例能力",
            "rubric": ["有核心定义", "有原理说明", "有具体例子"],
        }
    if index == 4:
        return {
            "id": question_id,
            "type": "scenario",
            "stem": f"场景题：学生混淆“{concept}”和相邻概念时，你会如何讲解“{title}”？",
            "standard_answer": "应先澄清概念边界，再用反例或对比例子说明差异，最后给出练习巩固。",
            "explanation": "概念混淆需要通过边界、反例和练习共同解决。",
            "difficulty": "提高",
            "assessment_point": f"{concept} 的概念辨析能力",
            "rubric": ["能澄清边界", "能给出反例或对比", "能设计巩固练习"],
        }
    return {
        "id": question_id,
        "type": "scenario",
        "stem": f"综合题：请结合“{title}”设计一个学习诊断路径，帮助学生定位薄弱点。",
        "standard_answer": "应包含概念检查、原理解释、例子迁移、常见误区排查和后续练习建议。",
        "explanation": "综合诊断要求把知识点组织成可执行的学习支持流程。",
        "difficulty": "综合",
        "assessment_point": f"{title} 的综合诊断与路径规划",
        "rubric": ["有概念检查", "有原理解释", "有例子迁移", "有误区排查", "有练习建议"],
    }


def build_chapter(idx: int, title: str, concepts: list[str]) -> dict:
    chapter_id = f"ai_intro/ch{idx:02d}"
    while len(concepts) < 4:
        concepts.append(title)
    c1, c2, c3, c4 = concepts[:4]
    objectives = [
        f"能用自己的话解释“{title}”要解决的核心问题，并区分它和相邻章节的关系。",
        f"能说清 {c1}、{c2}、{c3}、{c4} 四个概念的输入、输出、适用条件和限制。",
        f"能把一个校园或企业场景抽象为“数据/状态、处理方法、评价指标、风险点”四部分。",
        f"能识别至少 2 个常见误区，并用反例说明为什么该误区会导致错误结论。",
        f"能完成一个最小 Python 实验，记录实验设置、结果现象和改进建议。",
    ]
    detailed_concepts = [
        f"{c1}：本章的起点概念。学习时先回答“对象是什么、从哪里来、边界在哪里”，再判断后续方法是否适用。",
        f"{c2}：本章的效果判断线索。它通常不能单独作为结论，需要结合数据分布、业务目标和风险成本共同解释。",
        f"{c3}：本章的核心方法或工具。掌握时要拆成输入准备、关键步骤、参数选择、输出解释四个环节。",
        f"{c4}：本章的失效或优化重点。它帮助学习者从“能跑”进一步理解“何时不可靠、怎样改进”。",
    ]
    concept_cards = [
        {
            "name": concept,
            "definition": f"{concept} 是理解“{title}”时必须掌握的基础单元。",
            "why_it_matters": "它决定了后续建模、评价或应用解释是否站得住。",
            "example": f"在校园学习推荐中，可以把“{concept}”映射为学生行为、推荐策略或反馈指标的一部分。",
            "check_question": f"如果换一个真实场景，你还能指出“{concept}”对应的数据或决策位置吗？",
        }
        for concept in concepts[:8]
    ]
    difficulties = [
        f"概念边界：容易把“{c1}”和最终结论混为一谈，需要回到任务定义。",
        f"评价口径：只看“{c2}”的单一数值会误判效果，应结合样本来源和使用场景。",
        f"流程迁移：掌握“{c3}”的步骤不等于能迁移，需要能解释每一步为什么必要。",
        f"失败诊断：遇到“{c4}”相关问题时，要先定位数据、方法还是评价环节出了偏差。",
        "实验表达：不仅要给出结果，还要说明实验假设、变量控制和可能的误差来源。",
    ]
    misconceptions = [
        f"误区：把“{c1}”当成固定结论。纠正：它是分析框架，需要结合任务条件解释。",
        f"误区：只看“{c2}”的单一结果。纠正：应结合多个指标与反例综合判断。",
        f"误区：会写“{c3}”流程就等于会应用。纠正：必须通过新场景迁移验证。",
        f"误区：忽略“{c4}”的前提假设。纠正：先确认数据质量、分布和约束再下结论。",
        "误区：把实验输出截图当成完整结论。纠正：结论必须包含实验设置、观察现象、原因分析和下一步改进。",
    ]
    real_cases = [
        f"真实案例 1（校园）：用“{title}”改进选课推荐，比较策略前后完课率和满意度。",
        f"真实案例 2（企业）：客服系统使用“{c3}”后，首次响应效率提升但误判率上升，需增加人工复核。",
        f"真实案例 3（公共服务）：将“{c2}”用于效果评估时，发现不同群体差异，需要补充公平性分析。",
    ]
    code_labs = [
        f"代码实验 1：用 Python 构造最小样本，验证“{c1}”在理想数据下的行为。",
        f"代码实验 2：引入噪声与边界样本，观察“{c4}”触发时模型表现变化。",
        f"代码实验 3：对比两种实现方案的“{c2}”，输出实验日志和结论表。",
    ]
    practice_questions = [build_question(chapter_id, title, concepts, index) for index in range(1, 6)]
    return {
        "id": chapter_id,
        "title": title,
        "objectives": objectives,
        "concepts": concepts[:8],
        "concept_cards": concept_cards,
        "detailed_concepts": detailed_concepts,
        "difficulties": difficulties,
        "misconceptions": misconceptions,
        "example": f"围绕“{title}”构造校园学习场景，比较输入、处理过程和输出。",
        "real_cases": real_cases,
        "practice_drafts": [item["stem"] for item in practice_questions],
        "practice_questions": practice_questions,
        "reading": ["教材对应章节", "课程讲义", "公开课程实验说明"],
        "code_labs": code_labs,
        "task": f"用 Python 或伪代码完成一个与“{title}”相关的小实验。",
    }


def chapter_from_markdown_module(idx: int, module: dict) -> dict:
    chapter_id = f"ai_intro/ch{idx:02d}"
    title = module["title"]
    points = module["points"]
    concepts = [clean_title(point["title"]) for point in points]
    while len(concepts) < 4:
        concepts.append(title)

    objectives = [
        f"能解释“{title}”的核心问题，并说明它在人工智能课程体系中的位置。",
        f"能准确说明本章至少 4 个核心知识点的定义、原理、例子和常见问法。",
        "能将知识点迁移到课程答疑、练习设计或真实应用场景中。",
        "能识别常见误区，并用反例或对比例子纠正错误理解。",
        "能基于知识库片段生成可追溯的学习资源或问答证据。",
    ]

    concept_cards = []
    detailed_concepts = []
    difficulties = []
    misconceptions = []
    real_cases = []
    code_labs = []
    reading = []
    for point in points:
        fields = point["fields"]
        name = clean_title(point["title"])
        core = normalize_field_value(fields.get("核心解释"))
        principle = normalize_field_value(fields.get("基本原理"))
        example = normalize_field_value(fields.get("典型例子"))
        scenario = normalize_field_value(fields.get("适用场景"))
        advantages = normalize_field_value(fields.get("优点"))
        limits = normalize_field_value(fields.get("局限"))
        key_info = "；".join(
            value
            for value in [
                normalize_field_value(fields.get("关键概念")),
                normalize_field_value(fields.get("关键参数")),
                normalize_field_value(fields.get("关键模块")),
                normalize_field_value(fields.get("完整流程")),
                normalize_field_value(fields.get("缓解方法")),
            ]
            if value
        )
        questions = normalize_field_value(fields.get("常见问法"))

        concept_cards.append(
            {
                "name": name,
                "definition": core or f"{name} 是“{title}”中的核心知识点。",
                "why_it_matters": principle or "它帮助学习者理解本章方法的适用条件和边界。",
                "example": example or scenario or f"可在“{title}”相关学习任务中作为解释或练习对象。",
                "check_question": questions.split("；")[0] if questions else f"你能用自己的话解释“{name}”吗？",
            }
        )
        detail_parts = [f"{name}：{core}"]
        if principle:
            detail_parts.append(f"基本原理：{principle}")
        if key_info:
            detail_parts.append(f"关键点：{key_info}")
        detailed_concepts.append("；".join(part for part in detail_parts if part))
        if limits:
            difficulties.append(f"{name} 的局限：{limits}")
        elif questions:
            difficulties.append(f"{name} 的学习难点：{questions}")
        if advantages or limits:
            misconceptions.append(
                f"误区：认为“{name}”在任何场景都适用。纠正：需要结合"
                f"{'优势：' + advantages if advantages else '适用条件'}"
                f"{'；局限：' + limits if limits else ''}综合判断。"
            )
        if example:
            real_cases.append(f"{name}：{example}")
        if scenario:
            code_labs.append(f"实践实验：围绕“{name}”构造一个小样本或伪代码案例，观察它在“{scenario}”中的效果。")
        if questions:
            reading.append(f"{name} 常见问法：{questions}")

    while len(difficulties) < 5:
        difficulties.append(f"概念迁移：需要把“{title}”中的定义、原理、例子和适用边界联系起来。")
    while len(concept_cards) < 4:
        concept_cards.append(
            {
                "name": f"{title} 章节综述",
                "definition": f"{title} 章节综述用于把本章核心知识点组织成完整学习框架。",
                "why_it_matters": "它帮助检索和资源生成在知识点较少的章节中仍保持足够上下文。",
                "example": f"围绕“{title}”回答定义、原理、例子和常见问法。",
                "check_question": f"你能把“{title}”中的核心概念串成一条学习路径吗？",
            }
        )
    while len(detailed_concepts) < 4:
        detailed_concepts.append(f"{title} 章节综述：本章需要结合核心解释、基本原理、典型例子和常见问法进行整体理解。")
    while len(misconceptions) < 5:
        misconceptions.append(f"误区：只记忆“{title}”术语。纠正：必须结合原理、例子和常见问法完成理解。")
    while len(real_cases) < 3:
        real_cases.append(f"真实案例：在课程答疑中用“{title}”知识点解释学生当前困惑，并给出可验证例子。")
    while len(code_labs) < 3:
        code_labs.append(f"代码实验：选择“{title}”中的一个核心概念，用伪代码或 Python 最小样例展示输入、处理和输出。")

    practice_questions = [build_question(chapter_id, title, concepts, index) for index in range(1, 6)]
    return {
        "id": chapter_id,
        "title": title,
        "objectives": objectives,
        "concepts": concepts[:8],
        "concept_cards": concept_cards,
        "detailed_concepts": detailed_concepts,
        "difficulties": difficulties[: max(5, min(len(difficulties), 12))],
        "misconceptions": misconceptions[: max(5, min(len(misconceptions), 12))],
        "example": f"围绕“{title}”组织课程答疑，按定义、原理、例子、误区和练习逐步展开。",
        "real_cases": real_cases[: max(3, min(len(real_cases), 12))],
        "practice_drafts": [item["stem"] for item in practice_questions],
        "practice_questions": practice_questions,
        "reading": reading[:12] or ["课程知识库对应章节", "课堂讲义", "配套练习题"],
        "code_labs": code_labs[: max(3, min(len(code_labs), 8))],
        "task": f"从“{title}”中选 2 个知识点，设计一个解释、例子和练习组成的学习资源。",
    }


def fallback_course() -> dict:
    return {
        "id": "ai_intro",
        "title": "人工智能导论",
        "chapters": [
            build_chapter(idx, title, concepts)
            for idx, (title, concepts) in enumerate(CHAPTER_BLUEPRINTS, start=1)
        ],
        "code_cases": code_cases(),
    }


def code_cases() -> list[dict]:
    return [
        {"id": "case_astar", "title": "A* 搜索路径规划", "chapter": "ai_intro/ch03"},
        {"id": "case_classifier", "title": "分类器与评估指标", "chapter": "ai_intro/ch08"},
        {"id": "case_rag", "title": "本地资料检索增强问答", "chapter": "ai_intro/ch13"},
        {"id": "case_nlp_eval", "title": "客服意图识别与错误分析", "chapter": "ai_intro/ch12"},
        {"id": "case_attention", "title": "自注意力 QKV 可视化", "chapter": "ai_intro/ch11"},
        {"id": "case_rl_bandit", "title": "探索与利用策略对比实验", "chapter": "ai_intro/ch10"},
    ]


def load_markdown_course() -> dict:
    modules = parse_knowledge_markdown()
    return {
        "id": "ai_intro",
        "title": "人工智能导论",
        "source": str(COURSE_KB_PATH),
        "chapters": [chapter_from_markdown_module(idx, module) for idx, module in enumerate(modules, start=1)],
        "code_cases": code_cases(),
    }


try:
    COURSE = load_markdown_course()
except Exception:  # noqa: BLE001
    COURSE = fallback_course()


def build_aliases() -> dict[str, list[str]]:
    aliases = {
        "人工智能概述": ["人工智能导论", "人工智能概述", "图灵测试", "弱人工智能", "强人工智能", "ai intro", "agi"],
        "智能体": ["智能体", "agent", "理性智能体", "环境类型", "peas"],
        "搜索算法": ["搜索", "启发式", "启发函数", "状态空间", "代价函数", "a*", "a 星", "路径规划", "贪婪搜索", "minimax", "剪枝"],
        "知识表示": ["知识表示", "谓词逻辑", "产生式", "语义网络", "框架", "知识图谱"],
        "推理方法": ["推理", "演绎", "归纳", "不确定性", "贝叶斯", "模糊逻辑"],
        "专家系统": ["专家系统", "推理机", "知识库", "mycin", "正向链", "反向链"],
        "机器学习基础": ["机器学习基础", "训练集", "验证集", "测试集", "泛化", "损失函数", "过拟合", "欠拟合", "正则化", "偏差", "方差"],
        "监督学习": ["监督学习", "分类", "回归", "决策树", "逻辑回归", "朴素贝叶斯", "knn", "svm", "随机森林", "gbdt"],
        "无监督学习": ["无监督学习", "聚类", "降维", "k-means", "主成分", "pca", "clustering"],
        "强化学习": ["强化学习", "状态", "动作", "奖励", "策略", "mdp", "q-learning", "探索", "利用", "reinforcement learning"],
        "神经网络与深度学习": ["神经网络", "深度学习", "感知机", "反向传播", "激活函数", "梯度下降", "transformer", "self-attention", "自注意力", "qkv", "位置编码", "多头注意力"],
        "自然语言处理": ["自然语言处理", "nlp", "分词", "token", "词向量", "embedding", "attention", "ner", "文本摘要", "语义检索", "向量数据库"],
        "大语言模型与知识库问答": ["大模型", "大语言模型", "提示词", "prompt", "rag", "top-k", "重排序", "幻觉", "知识库问答", "kbqa", "llm"],
    }
    for chapter in COURSE["chapters"]:
        title = chapter["title"]
        chapter_aliases = aliases.setdefault(title, [])
        for concept in chapter.get("concepts", []):
            if concept not in chapter_aliases:
                chapter_aliases.append(concept)
    return aliases


CHAPTER_ALIASES = build_aliases()

GENERIC_CHAPTER_TERMS = {"机器学习", "人工智能", "ai"}


def _norm_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _chapter_by_title(title: str) -> dict | None:
    normalized = _norm_text(title)
    if not normalized:
        return None
    for chapter in COURSE["chapters"]:
        if normalized == _norm_text(chapter["title"]):
            return chapter
    return None


def match_chapter(*texts: str, fallback: str | None = None) -> dict:
    """Return a chapter match with confidence and warnings instead of silently defaulting."""
    joined = "\n".join(text for text in texts if text).strip()
    normalized = _norm_text(joined)
    fallback_chapter = _chapter_by_title(fallback or "") if fallback else None

    if not normalized:
        chapter = fallback_chapter or COURSE["chapters"][0]
        return {
            "chapter": chapter,
            "confidence": 0.45 if fallback_chapter else 0.2,
            "source": "profile" if fallback_chapter else "default",
            "warnings": [] if fallback_chapter else ["未识别明确章节，已使用课程默认章节。"],
        }

    scores: list[tuple[float, dict, list[str]]] = []
    for chapter in COURSE["chapters"]:
        title = chapter["title"]
        aliases = [title, *chapter.get("concepts", []), *CHAPTER_ALIASES.get(title, [])]
        hits = []
        score = 0.0
        for alias in aliases:
            token = _norm_text(alias)
            if not token:
                continue
            if token == normalized:
                score += 4.0
                hits.append(alias)
            elif token in normalized:
                score += 2.0 if alias == title else 1.0
                hits.append(alias)
        if title == "机器学习基础" and any(term in normalized for term in GENERIC_CHAPTER_TERMS):
            score -= 0.8
        if hits:
            scores.append((score, chapter, hits))

    if scores:
        scores.sort(key=lambda item: item[0], reverse=True)
        score, chapter, hits = scores[0]
        confidence = 0.95 if score >= 3.0 else 0.78 if score >= 1.5 else 0.62
        return {
            "chapter": chapter,
            "confidence": confidence,
            "source": "explicit",
            "matched_terms": hits[:6],
            "warnings": [] if confidence >= 0.7 else [f"章节匹配置信度较低，已根据关键词推断为{chapter['title']}。"],
        }

    chapter = fallback_chapter or COURSE["chapters"][0]
    return {
        "chapter": chapter,
        "confidence": 0.55 if fallback_chapter else 0.2,
        "source": "profile" if fallback_chapter else "default",
        "matched_terms": [],
        "warnings": [] if fallback_chapter else ["未识别明确章节，已使用课程默认章节。"],
    }


def infer_target_concepts(*texts: str, chapter_title: str = "") -> list[str]:
    normalized = _norm_text("\n".join(text for text in texts if text))
    chapter = _chapter_by_title(chapter_title) or match_chapter(normalized).get("chapter")
    concepts: list[str] = []
    for concept in chapter.get("concepts", []):
        if _norm_text(concept) in normalized:
            concepts.append(concept)
    for alias in CHAPTER_ALIASES.get(chapter["title"], []):
        if _norm_text(alias) in normalized and alias not in concepts and alias != chapter["title"]:
            concepts.append(alias)
    return concepts[:8]


def find_chapter(keyword: str):
    return match_chapter(keyword).get("chapter")


def question_bank() -> list[dict]:
    questions = []
    for chapter in COURSE["chapters"]:
        for question in chapter["practice_questions"]:
            questions.append(
                {
                    "id": question["id"],
                    "chapter_id": chapter["id"],
                    "type": question["type"],
                    "stem": question["stem"],
                    "answer": question["standard_answer"],
                    "analysis": question["explanation"],
                    "difficulty": question["difficulty"],
                    "assessment_point": question["assessment_point"],
                    "options": question.get("options", []),
                    "rubric": question.get("rubric", []),
                }
            )
    return questions
