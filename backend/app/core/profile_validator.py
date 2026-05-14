from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .profile_normalizer import ProfileNormalizer


class ProfileValidator:
    """Heuristic safety checks for LLM profile fusion output."""

    LIST_FIELDS = ["knowledge_base", "preferred_modalities", "weak_points", "mistake_patterns", "interests"]
    REQUIRED_STRING_FIELDS = ["major", "education_level", "course", "current_chapter", "learning_goal", "cognitive_style", "time_budget"]
    CRITICAL_FIELDS = ["learning_goal", "weak_points", "time_budget"]
    FREE_FORM_LIST_FIELDS = {"knowledge_base", "weak_points", "interests"}

    def __init__(
        self,
        normalizer: ProfileNormalizer | None = None,
        drop_ratio_threshold: float = 0.5,
        known_tag_min_length: int = 2,
    ):
        self.normalizer = normalizer or ProfileNormalizer()
        self.drop_ratio_threshold = drop_ratio_threshold
        self.known_tag_min_length = known_tag_min_length

    def _as_list(self, profile: Mapping[str, Any], field: str) -> list[str]:
        value = profile.get(field, [])
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, list):
            return len([item for item in value if str(item).strip()]) == 0
        return False

    def _mentioned_in_chat(self, tag: str, user_chat: str) -> bool:
        compact_tag = re.sub(r"\s+", "", tag).lower()
        compact_chat = re.sub(r"\s+", "", user_chat or "").lower()
        return bool(compact_tag and compact_tag in compact_chat)

    def _looks_unknown_tag(self, tag: str, user_chat: str) -> bool:
        normalized = self.normalizer.normalize_tag(tag)
        key = self.normalizer._key(tag)
        if len(key) < self.known_tag_min_length:
            return True
        if normalized != re.sub(r"\s+", "", str(tag).strip()):
            return False
        if key in self.normalizer.alias_map:
            return False
        if self._mentioned_in_chat(tag, user_chat):
            return False
        if re.search(r"[^\w\u4e00-\u9fff+#.-]", tag):
            return True
        return True

    def evaluate_fusion(self, old_profile: dict, new_profile: dict, user_chat: str) -> dict:
        warnings: list[str] = []
        high_risk = False
        score = 1.0

        for field in self.LIST_FIELDS:
            old_items = self._as_list(old_profile, field)
            new_items = self._as_list(new_profile, field)
            if len(old_items) >= 2 and len(new_items) < len(old_items) * self.drop_ratio_threshold:
                warnings.append(
                    f"{field} 从 {len(old_items)} 项下降到 {len(new_items)} 项，疑似画像信息丢失。"
                )
                score -= 0.2
                if field in {"weak_points", "knowledge_base"}:
                    high_risk = True

        old_goal = str(old_profile.get("learning_goal", "")).strip()
        new_goal = str(new_profile.get("learning_goal", "")).strip()
        if old_goal and not new_goal:
            warnings.append("learning_goal 被清空，疑似目标信息丢失。")
            score -= 0.25
            high_risk = True
        elif old_goal and new_goal and old_goal != new_goal and not self._mentioned_in_chat(new_goal, user_chat):
            warnings.append("learning_goal 发生变化，但新目标没有明显来自用户最新对话，建议确认。")
            score -= 0.15
            high_risk = True

        for field in self.REQUIRED_STRING_FIELDS:
            if not self._is_empty_value(old_profile.get(field)) and self._is_empty_value(new_profile.get(field)):
                warnings.append(f"{field} 为空，画像关键字段异常。")
                score -= 0.12
                if field in self.CRITICAL_FIELDS:
                    high_risk = True

        for field in self.LIST_FIELDS:
            if not isinstance(new_profile.get(field, []), list):
                warnings.append(f"{field} 应为列表类型，当前类型异常。")
                score -= 0.18
                high_risk = True
                continue

            for tag in self._as_list(new_profile, field):
                if self._looks_unknown_tag(tag, user_chat):
                    warnings.append(f"{field} 出现未知或异常标签：{tag}")
                    score -= 0.08
                    if field not in self.FREE_FORM_LIST_FIELDS:
                        high_risk = True

        mastery = new_profile.get("mastery")
        if not isinstance(mastery, (int, float)) or not 0 <= float(mastery) <= 1:
            warnings.append("mastery 应为 0-1 之间的数值。")
            score -= 0.2
            high_risk = True

        confidence_score = round(max(0.0, min(1.0, score)), 2)
        return {
            "is_valid": confidence_score >= 0.65 and not high_risk,
            "confidence_score": confidence_score,
            "warnings": warnings,
            "requires_confirmation": high_risk or confidence_score < 0.75,
        }
