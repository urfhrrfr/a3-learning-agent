COURSE = {
    "id": "ai_intro",
    "title": "人工智能导论",
    "chapters": [
        {
            "id": f"ai_intro/ch{idx:02d}",
            "title": title,
            "objectives": ["说清核心概念", "能用例子解释方法", "完成一组基础练习"],
            "concepts": concepts,
            "difficulties": ["概念边界", "方法适用条件", "从公式迁移到案例"],
            "misconceptions": ["把术语当作结论", "忽略数据假设", "只记流程不理解评价"],
            "example": f"围绕“{title}”构造校园学习场景，比较输入、处理过程和输出。",
            "practice_drafts": [f"{title} 选择题 {n}: 判断关键概念的适用场景。" for n in range(1, 6)],
            "reading": ["教材对应章节", "课程讲义", "公开课程实验说明"],
            "task": f"用 Python 或伪代码完成一个与“{title}”相关的小实验。",
        }
        for idx, (title, concepts) in enumerate(
            [
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
            ],
            start=1,
        )
    ],
    "code_cases": [
        {"id": "case_astar", "title": "A* 搜索路径规划", "chapter": "ai_intro/ch02"},
        {"id": "case_classifier", "title": "鸢尾花分类器与评估指标", "chapter": "ai_intro/ch05"},
        {"id": "case_rag", "title": "本地资料检索增强问答", "chapter": "ai_intro/ch11"},
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
        for idx in range(1, 6):
            questions.append(
                {
                    "id": f"{chapter['id']}#q{idx:02d}",
                    "chapter_id": chapter["id"],
                    "type": ["choice", "true_false", "short_answer", "code_reading", "scenario"][idx - 1],
                    "stem": f"{chapter['title']} 题目 {idx}: 请解释或判断核心概念“{chapter['concepts'][0]}”的使用场景。",
                    "answer": "应结合定义、输入输出、适用条件与反例说明。",
                }
            )
    return questions
