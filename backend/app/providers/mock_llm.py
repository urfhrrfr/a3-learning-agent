import json
import re

from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Deterministic provider used when no real model key is configured."""

    name = "mock"

    def complete(self, prompt: str) -> str:
        if "相关性裁判" in prompt or "Reranker" in prompt:
            ids = re.findall(r"id=([^\n]+)", prompt)
            results = [
                {
                    "id": fragment_id.strip(),
                    "relevance_score": round(max(0.55, 0.95 - index * 0.08), 2),
                    "reason": "模拟相关性裁判：按候选片段顺序返回高相关片段。",
                }
                for index, fragment_id in enumerate(ids[:5])
            ]
            return json.dumps(results, ensure_ascii=False)
        if "画像" in prompt:
            return "已抽取学生目标、薄弱点、学习风格和资源偏好。"
        if "审核" in prompt:
            return "内容引用课程知识库，难度与画像匹配，审核通过。"
        return "基于人工智能导论知识库生成结构化教学内容。"
