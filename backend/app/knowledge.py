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


def build_chapter(idx: int, title: str, concepts: list[str]) -> dict:
    chapter_id = f"ai_intro/ch{idx:02d}"
    c1, c2, c3, c4 = concepts
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
        for concept in concepts
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
    practice_questions = [
        {
            "id": f"{chapter_id}#q01",
            "type": "choice",
            "stem": f"在“{title}”中，下列哪一项最能体现“{c1}”的作用？",
            "standard_answer": "应选择能同时描述输入条件、处理过程与输出影响的选项。",
            "explanation": f"{c1} 不只是术语名称，而是用于解释任务机制的核心单位。",
            "difficulty": "基础",
            "assessment_point": f"{c1} 的概念识别与任务映射",
            "options": ["只看术语定义，不看任务目标", "同时检查输入条件、处理逻辑与输出效果", "优先选择训练误差最低方案", "直接套用旧场景结论"],
            "rubric": ["能指出输入条件", "能说明处理过程", "能联系输出影响"],
        },
        {
            "id": f"{chapter_id}#q02",
            "type": "true_false",
            "stem": f"判断：只要“{c2}”结果好，就说明系统已经可直接上线。",
            "standard_answer": "错误",
            "explanation": "上线还需检查分布漂移、风险成本、鲁棒性和可解释性。",
            "difficulty": "基础",
            "assessment_point": f"{c2} 的评价边界",
            "options": ["正确", "错误"],
            "rubric": ["能识别单一指标的局限", "能补充分布漂移或风险成本"],
        },
        {
            "id": f"{chapter_id}#q03",
            "type": "short_answer",
            "stem": f"简答：请用 3 句话说明“{c3}”如何落地到一个实际场景。",
            "standard_answer": "应包含场景目标、输入数据、关键步骤与评估方法。",
            "explanation": "能说清“为什么做、怎么做、如何验证”才算真正理解。",
            "difficulty": "应用",
            "assessment_point": f"{c3} 的场景迁移能力",
            "rubric": ["有明确场景目标", "有输入数据或状态描述", "有关键步骤", "有评价方法"],
        },
        {
            "id": f"{chapter_id}#q04",
            "type": "code_reading",
            "stem": f"阅读伪代码并指出其在“{c4}”相关环节的风险点与改进建议。",
            "standard_answer": "应指出至少 1 个数据或评估风险，并给出可执行修复方案。",
            "explanation": "代码理解题重点是发现假设漏洞，而不是复述语法。",
            "difficulty": "提高",
            "assessment_point": f"{c4} 的风险识别与实验改进",
            "rubric": ["能定位风险点", "能说明风险影响", "能提出可执行修复方案"],
        },
        {
            "id": f"{chapter_id}#q05",
            "type": "scenario",
            "stem": f"场景题：某系统在新用户上表现下降，请结合“{title}”提出诊断路径。",
            "standard_answer": "先验证数据差异，再检查模型/规则适用条件，最后给出分步改进计划。",
            "explanation": "先定位问题来源，再制定低风险迭代方案，避免盲目调参。",
            "difficulty": "综合",
            "assessment_point": f"{title} 的综合诊断与路径规划",
            "rubric": ["能提出数据检查", "能分析方法适用条件", "能给出分步改进计划", "能说明验证方式"],
        },
    ]
    return {
        "id": chapter_id,
        "title": title,
        "objectives": objectives,
        "concepts": concepts,
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


COURSE = {
    "id": "ai_intro",
    "title": "人工智能导论",
    "chapters": [build_chapter(idx, title, concepts) for idx, (title, concepts) in enumerate(CHAPTER_BLUEPRINTS, start=1)],
    "code_cases": [
        {"id": "case_astar", "title": "A* 搜索路径规划", "chapter": "ai_intro/ch02"},
        {"id": "case_classifier", "title": "鸢尾花分类器与评估指标", "chapter": "ai_intro/ch05"},
        {"id": "case_rag", "title": "本地资料检索增强问答", "chapter": "ai_intro/ch11"},
        {"id": "case_nlp_eval", "title": "客服意图识别与错误分析", "chapter": "ai_intro/ch08"},
        {"id": "case_cv_aug", "title": "图像增强对识别稳定性的影响", "chapter": "ai_intro/ch09"},
        {"id": "case_rl_bandit", "title": "多臂老虎机策略对比实验", "chapter": "ai_intro/ch10"},
    ],
}


def find_chapter(keyword: str):
    for chapter in COURSE["chapters"]:
        if keyword in chapter["title"]:
            return chapter
    if "机器学习" in keyword:
        return COURSE["chapters"][3]
    return COURSE["chapters"][0]


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
