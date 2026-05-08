class MockLLMProvider:
    """Deterministic provider used when no real model key is configured."""

    def complete(self, prompt: str) -> str:
        if "画像" in prompt:
            return "已抽取学生目标、薄弱点、学习风格和资源偏好。"
        if "审核" in prompt:
            return "内容引用课程知识库，难度与画像匹配，审核通过。"
        return "基于人工智能导论知识库生成结构化教学内容。"
