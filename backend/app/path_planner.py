"""学习路径规划器模块"""

import json
import re
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from uuid import uuid4

from .providers.factory import get_llm_provider
from .providers.base import BaseLLMProvider, LLMProviderError
from .schemas import Profile
from .path_prompts import (
    build_path_planning_prompt,
    build_path_adjustment_prompt,
    build_resource_priority_prompt
)


class LearningPath:
    """学习路径数据结构"""
    
    def __init__(self, path_id: str = None):
        self.id = path_id or f"path_{uuid4().hex[:8]}"
        self.profile_version = 1
        self.mastery = 0.0
        self.overall_goal = ""
        self.adjustment_reason = ""
        self.steps: List[Dict[str, Any]] = []
        self.created_at = datetime.now(timezone.utc).astimezone().isoformat()
        self.updated_at = self.created_at
    
    def model_dump(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "profile_version": self.profile_version,
            "mastery": self.mastery,
            "overall_goal": self.overall_goal,
            "adjustment_reason": self.adjustment_reason,
            "steps": self.steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LearningPath":
        """从字典创建"""
        path = cls(data.get("id"))
        path.profile_version = data.get("profile_version", 1)
        path.mastery = data.get("mastery", 0.0)
        path.overall_goal = data.get("overall_goal", "")
        path.adjustment_reason = data.get("adjustment_reason", "")
        path.steps = data.get("steps", [])
        path.created_at = data.get("created_at", datetime.now(timezone.utc).astimezone().isoformat())
        path.updated_at = data.get("updated_at", path.created_at)
        return path


class LearningProgress:
    """学习进度追踪器"""
    
    def __init__(self, path_id: str):
        self.path_id = path_id
        self.completed_steps: List[str] = []
        self.in_progress_step: Optional[str] = None
        self.resource_usage: List[Dict[str, Any]] = []
        self.quiz_scores: List[Dict[str, Any]] = []
        self.total_time_spent_minutes = 0
        self.last_activity_at = datetime.now(timezone.utc).astimezone().isoformat()
    
    def mark_step_completed(self, step_id: str, time_spent_minutes: int = 0):
        """标记步骤完成"""
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
        self.total_time_spent_minutes += time_spent_minutes
        self.last_activity_at = datetime.now(timezone.utc).astimezone().isoformat()
    
    def record_resource_usage(self, resource_id: str, time_spent_minutes: int, completed: bool):
        """记录资源使用"""
        self.resource_usage.append({
            "resource_id": resource_id,
            "time_spent_minutes": time_spent_minutes,
            "completed": completed,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat()
        })
        self.total_time_spent_minutes += time_spent_minutes
        self.last_activity_at = datetime.now(timezone.utc).astimezone().isoformat()
    
    def record_quiz_score(self, quiz_id: str, score: float, total_questions: int):
        """记录测验分数"""
        self.quiz_scores.append({
            "quiz_id": quiz_id,
            "score": score,
            "total_questions": total_questions,
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat()
        })
    
    def get_completion_rate(self, total_steps: int) -> float:
        """获取完成率"""
        if total_steps == 0:
            return 0.0
        return len(self.completed_steps) / total_steps
    
    def model_dump(self) -> dict:
        """转为字典"""
        return {
            "path_id": self.path_id,
            "completed_steps": self.completed_steps,
            "in_progress_step": self.in_progress_step,
            "resource_usage": self.resource_usage,
            "quiz_scores": self.quiz_scores,
            "total_time_spent_minutes": self.total_time_spent_minutes,
            "last_activity_at": self.last_activity_at
        }


class PathPlanner:
    """学习路径规划器"""
    
    def __init__(self, llm: Optional[BaseLLMProvider] = None):
        self.llm = llm or get_llm_provider()
        self.confidence_threshold = 0.6
        self._difficulty_order = ["入门", "基础", "提高", "进阶"]
        self._max_retries = 2
        self._retry_delay = 2
    
    def _extract_json_from_response(self, text: str) -> Optional[Dict]:
        """从响应中提取JSON"""
        text = text.strip()
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _call_llm_with_retry(self, prompt: str) -> Optional[str]:
        """带重试的LLM调用"""
        for attempt in range(self._max_retries + 1):
            try:
                start = time.time()
                response = self.llm.complete(prompt)
                elapsed = time.time() - start
                print(f"LLM调用成功，耗时: {elapsed:.2f}s")
                return response
            except Exception as e:
                print(f"LLM调用失败 (尝试 {attempt + 1}/{self._max_retries + 1}): {e}")
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)
        return None

    def _assessment_weak_points(self, assessment: Optional[Dict]) -> List[str]:
        """从不同形态的测评报告中提取薄弱点。"""
        if not assessment:
            return []

        raw = assessment.get("weak_points") or assessment.get("assessment", {}).get("weak_points", [])
        points = []
        for item in raw:
            if isinstance(item, dict):
                topic = item.get("topic") or item.get("name") or item.get("title")
            else:
                topic = str(item)
            if topic and topic not in points:
                points.append(topic)
        return points

    def _assessment_mistake_patterns(self, assessment: Optional[Dict]) -> List[str]:
        if not assessment:
            return []
        raw = assessment.get("mistake_patterns") or assessment.get("assessment", {}).get("mistake_patterns", [])
        return [str(item) for item in raw if item]

    def _target_difficulties(self, mastery: float) -> List[str]:
        if mastery < 0.35:
            return ["入门", "基础"]
        if mastery < 0.65:
            return ["基础", "提高"]
        return ["提高", "进阶"]

    def _difficulty_label(self, mastery: float) -> str:
        if mastery < 0.35:
            return "先补概念和最小例子"
        if mastery < 0.65:
            return "在基础理解上加入迁移练习"
        return "提高挑战度，加入综合应用"

    def _modality_aliases(self, modality: str) -> List[str]:
        mapping = {
            "图解": ["mindmap", "diagram", "mermaid", "concept_map", "图", "图解"],
            "代码": ["code", "code_case", "python", "代码", "实验"],
            "代码案例": ["code", "code_case", "python", "代码", "实验"],
            "短视频": ["video", "media_script", "script", "视频", "脚本"],
            "视频": ["video", "media_script", "script", "视频", "脚本"],
            "练习": ["quiz", "exercise", "practice", "测验", "练习"],
        }
        return mapping.get(modality, [modality])

    def _resource_score(
        self,
        resource: Dict,
        concept: str,
        profile: Profile,
        assessment: Optional[Dict] = None,
    ) -> tuple[float, List[str]]:
        score = 0.2
        reasons = []
        title = resource.get("title", "")
        resource_type = resource.get("type", "")
        difficulty = resource.get("difficulty", "基础")
        searchable = f"{title} {resource_type} {' '.join(resource.get('target_concepts', []))}"

        if concept and concept in searchable:
            score += 0.35
            reasons.append(f"直接覆盖当前要补的「{concept}」")

        weak_points = list(profile.weak_points) + self._assessment_weak_points(assessment)
        matched_weak = [point for point in weak_points if point and point in searchable]
        if matched_weak:
            score += 0.25
            reasons.append(f"匹配薄弱点：{matched_weak[0]}")

        matched_modalities = []
        for modality in profile.preferred_modalities:
            if any(alias.lower() in searchable.lower() for alias in self._modality_aliases(modality)):
                matched_modalities.append(modality)
        if matched_modalities:
            score += 0.18
            reasons.append(f"符合偏好模态：{matched_modalities[0]}")

        target_difficulties = self._target_difficulties(profile.mastery)
        if difficulty in target_difficulties:
            score += 0.16
            reasons.append(f"难度为{difficulty}，适合当前掌握度{profile.mastery:.2f}")
        elif profile.mastery < 0.35 and difficulty in ["提高", "进阶"]:
            score -= 0.12
            reasons.append("难度略高，排在概念补强之后")

        mistake_patterns = list(profile.mistake_patterns) + self._assessment_mistake_patterns(assessment)
        if mistake_patterns and resource_type in {"quiz", "code_case", "exercise"}:
            score += 0.12
            reasons.append(f"可针对「{mistake_patterns[0]}」做输出检验")

        estimated_time = resource.get("estimated_time_minutes", 30)
        if estimated_time <= profile_time_budget_to_minutes(profile.time_budget):
            score += 0.04
            reasons.append("时长符合当前学习预算")

        feedback_action = resource.get("feedback_action", "neutral")
        if feedback_action == "favorite":
            score += 0.2
            reasons.append("用户已收藏，后续推送优先保留")
        elif feedback_action == "hidden":
            score -= 1.0
            reasons.append("用户已屏蔽，后续推送降权")

        return max(0.0, min(1.0, score)), reasons

    def _rank_resources(
        self,
        profile: Profile,
        resources: List[Dict],
        concept: str,
        assessment: Optional[Dict] = None,
        limit: int = 3,
    ) -> List[Dict]:
        ranked = []
        for resource in resources:
            score, reasons = self._resource_score(resource, concept, profile, assessment)
            ranked.append((score, reasons, resource))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = []
        for priority, (score, reasons, resource) in enumerate(ranked[:limit], 1):
            reason = "；".join(reasons[:2]) if reasons else f"作为「{concept}」的补充材料"
            selected.append({
                "id": resource.get("id", f"res_{priority}"),
                "reason": reason,
                "priority": priority,
                "score": round(score, 2),
            })
        return selected
    
    def _build_default_path(
        self,
        profile: Profile,
        available_resources: List[Dict],
        assessment_report: Optional[Dict] = None,
    ) -> LearningPath:
        """构建默认路径（后备方案）"""
        path = LearningPath()
        path.profile_version = profile.version
        path.mastery = profile.mastery
        path.overall_goal = profile.learning_goal
        path.adjustment_reason = (
            f"基于画像、资源和测评线索的规则规划：{self._difficulty_label(profile.mastery)}"
        )
        
        assessment_weak_points = self._assessment_weak_points(assessment_report)
        mistake_patterns = self._assessment_mistake_patterns(assessment_report) or profile.mistake_patterns
        concepts = []
        for concept in assessment_weak_points + profile.weak_points:
            if concept and concept not in concepts:
                concepts.append(concept)
        if mistake_patterns:
            concepts.append(f"{mistake_patterns[0]}纠偏练习")
        concepts += ["机器学习概述", "监督学习基础"]
        
        steps = []
        for i, concept in enumerate(concepts[:5], 1):
            step_id = f"step_{i:02d}"
            step_resources = self._rank_resources(
                profile,
                available_resources,
                concept,
                assessment_report,
            )
            difficulty = self._target_difficulties(profile.mastery)[min(i - 1, 1)]
            time_base = 25 if profile.mastery < 0.35 else 35 if profile.mastery < 0.65 else 45
            mastery_increase = 0.12 if profile.mastery < 0.35 else 0.09 if profile.mastery < 0.65 else 0.06
            reason_parts = [
                f"当前掌握度 {profile.mastery:.2f}，本步采用{difficulty}难度",
            ]
            if concept in profile.weak_points or concept in assessment_weak_points:
                reason_parts.append(f"优先处理薄弱点「{concept}」")
            if mistake_patterns:
                reason_parts.append(f"结合错误模式「{mistake_patterns[0]}」安排输出检验")
            if profile.preferred_modalities:
                reason_parts.append(f"资源排序优先照顾「{profile.preferred_modalities[0]}」偏好")
            
            steps.append({
                "id": step_id,
                "title": f"{difficulty}：{concept}",
                "objective": f"围绕{concept}完成理解、例子复述和一次迁移练习",
                "recommended_resources": step_resources,
                "recommended_resource_ids": [item["id"] for item in step_resources],
                "reason": "；".join(reason_parts),
                "estimated_minutes": time_base,
                "prerequisites": [f"step_{i-1:02d}"] if i > 1 else [],
                "status": "todo",
                "expected_mastery_increase": mastery_increase
            })
        
        path.steps = steps
        return path
    
    def plan(
        self,
        profile: Profile,
        available_resources: List[Dict] = None,
        assessment_report: Optional[Dict] = None,
    ) -> Dict:
        """生成学习路径"""
        available_resources = available_resources or []
        
        try:
            prompt = build_path_planning_prompt(
                profile.model_dump(),
                None,
                available_resources,
                assessment_report
            )
            print(f"开始生成学习路径，提示词长度: {len(prompt)}")
            
            response = self._call_llm_with_retry(prompt)
            if not response:
                print("LLM调用失败，使用后备方案")
                raise Exception("LLM调用失败")
            
            result = self._extract_json_from_response(response)
            
            if result and "learning_path" in result:
                confidence = result.get("confidence", 0.5)
                if confidence >= self.confidence_threshold:
                    path_data = result["learning_path"]
                    path = LearningPath.from_dict(path_data)
                    return {
                        "learning_path": path.model_dump(),
                        "resource_priority": result.get("resource_priority", []),
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", "LLM生成路径"),
                        "source": "llm"
                    }
        except Exception as e:
            print(f"路径规划失败: {e}")
        
        path = self._build_default_path(profile, available_resources, assessment_report)
        return {
            "learning_path": path.model_dump(),
            "resource_priority": self._fallback_prioritize(profile, assessment_report or {}, available_resources)["prioritized_resources"],
            "confidence": 0.68,
            "reasoning": path.adjustment_reason,
            "source": "fallback"
        }
    
    def adjust(self, current_path: Dict, assessment: Dict, profile: Profile) -> Dict:
        """根据评估结果调整路径"""
        try:
            prompt = build_path_adjustment_prompt(current_path, assessment, profile.model_dump())
            response = self._call_llm_with_retry(prompt)
            
            if response:
                result = self._extract_json_from_response(response)
                
                if result and "adjusted_path" in result:
                    confidence = result.get("confidence", 0.5)
                    if confidence >= self.confidence_threshold:
                        path = LearningPath.from_dict(result["adjusted_path"])
                        return {
                            "learning_path": path.model_dump(),
                            "adjustments": result.get("adjustments", []),
                            "confidence": confidence,
                            "reasoning": result.get("reasoning", "LLM调整路径"),
                            "source": "llm"
                        }
        except Exception as e:
            print(f"路径调整失败: {e}")
        
        return self._fallback_adjust(current_path, assessment, profile)
    
    def _fallback_adjust(self, current_path: Dict, assessment: Dict, profile: Profile) -> Dict:
        """后备路径调整"""
        adjusted_path = LearningPath.from_dict(current_path)
        adjusted_path.updated_at = datetime.now(timezone.utc).astimezone().isoformat()
        mistake_patterns = self._assessment_mistake_patterns(assessment) or profile.mistake_patterns
        adjusted_path.adjustment_reason = "基于测评薄弱点和错误模式的动态调整"
        
        adjustments = []
        mastery_delta = assessment.get("mastery_delta", 0)
        weak_points = assessment.get("assessment", {}).get("weak_points", [])
        
        if mastery_delta < -0.05:
            for step in adjusted_path.steps:
                if step["status"] == "todo":
                    step["status"] = "pending_review"
                    adjustments.append({
                        "type": "modify",
                        "step_id": step["id"],
                        "reason": "掌握度下降，需要重新评估当前步骤"
                    })
                    break
        elif mastery_delta > 0.1:
            for step in adjusted_path.steps:
                if step["status"] == "todo":
                    step["status"] = "in_progress"
                    adjustments.append({
                        "type": "modify",
                        "step_id": step["id"],
                        "reason": "掌握度提升，提前开始下一步"
                    })
                    break
        
        if weak_points:
            for wp in weak_points[:2]:
                topic = wp.get("topic", "")
                found = False
                for step in adjusted_path.steps:
                    if topic in step["title"]:
                        step["status"] = "in_progress"
                        step["reason"] = (
                            f"测评显示「{topic}」仍是薄弱点，先回到这一步补强；"
                            f"错误模式：{mistake_patterns[0] if mistake_patterns else '待观察'}"
                        )
                        found = True
                        break
                
                if not found and len(adjusted_path.steps) < 8:
                    new_step = {
                        "id": f"step_{len(adjusted_path.steps)+1:02d}",
                        "title": f"强化{topic}",
                        "objective": f"针对薄弱点{topic}进行专项练习",
                        "recommended_resources": [],
                        "recommended_resource_ids": [],
                        "reason": (
                            f"测评新增薄弱点「{topic}」，需要插入专项练习；"
                            f"下一步重点纠正「{mistake_patterns[0] if mistake_patterns else '概念迁移'}」"
                        ),
                        "estimated_minutes": 30,
                        "prerequisites": [adjusted_path.steps[-1]["id"]] if adjusted_path.steps else [],
                        "status": "in_progress",
                        "expected_mastery_increase": 0.08
                    }
                    adjusted_path.steps.insert(1, new_step)
                    adjustments.append({
                        "type": "add",
                        "step_id": new_step["id"],
                        "reason": f"添加薄弱点{topic}的专项练习"
                    })
        
        return {
            "learning_path": adjusted_path.model_dump(),
            "adjustments": adjustments,
            "confidence": 0.6,
            "reasoning": "基于评估结果的规则调整",
            "source": "fallback"
        }
    
    def prioritize_resources(self, profile: Profile, assessment: Dict, resources: List[Dict]) -> Dict:
        """资源优先级排序"""
        if not resources:
            return {"prioritized_resources": [], "confidence": 0.3}
        
        try:
            prompt = build_resource_priority_prompt(profile.model_dump(), assessment, resources)
            response = self._call_llm_with_retry(prompt)
            
            if response:
                result = self._extract_json_from_response(response)
                
                if result and "prioritized_resources" in result:
                    return {
                        "prioritized_resources": result["prioritized_resources"],
                        "confidence": result.get("confidence", 0.5),
                        "source": "llm"
                    }
        except Exception as e:
            print(f"资源优先级排序失败: {e}")
        
        return self._fallback_prioritize(profile, assessment, resources)
    
    def _fallback_prioritize(self, profile: Profile, assessment: Dict, resources: List[Dict]) -> Dict:
        """后备资源优先级排序"""
        prioritized = []
        
        for resource in resources:
            concept = ""
            for point in self._assessment_weak_points(assessment) + profile.weak_points:
                title = resource.get("title", "")
                if point and point in title:
                    concept = point
                    break
            score, reasons = self._resource_score(resource, concept, profile, assessment)
            
            prioritized.append({
                "id": resource.get("id", ""),
                "priority": len(prioritized) + 1,
                "score": round(score, 2),
                "reason": "；".join(reasons[:3]) if reasons else "作为当前路径的补充资源"
            })
        
        prioritized.sort(key=lambda x: x["score"], reverse=True)
        
        for i, item in enumerate(prioritized, 1):
            item["priority"] = i
        
        return {
            "prioritized_resources": prioritized,
            "confidence": 0.6,
            "source": "fallback"
        }
    
    def generate_progress_summary(self, path: Dict, progress: LearningProgress) -> Dict:
        """生成进度摘要"""
        total_steps = len(path.get("steps", []))
        completed_count = len(progress.completed_steps)
        completion_rate = progress.get_completion_rate(total_steps)
        
        avg_quiz_score = 0.0
        if progress.quiz_scores:
            avg_quiz_score = sum(q["score"] for q in progress.quiz_scores) / len(progress.quiz_scores)
        
        time_budget = profile_time_budget_to_minutes(progress.profile.time_budget) if hasattr(progress, 'profile') else 45
        time_used = progress.total_time_spent_minutes
        time_efficiency = min(1.0, (completion_rate * 100) / max(1, time_used / (time_budget / 60)))
        
        return {
            "path_id": path["id"],
            "total_steps": total_steps,
            "completed_steps": completed_count,
            "completion_rate": round(completion_rate, 2),
            "in_progress_step": progress.in_progress_step,
            "avg_quiz_score": round(avg_quiz_score, 2),
            "total_time_spent_minutes": time_used,
            "time_efficiency": round(time_efficiency, 2),
            "last_activity_at": progress.last_activity_at,
            "recommendations": self._generate_recommendations(path, progress, completion_rate, avg_quiz_score)
        }
    
    def _generate_recommendations(self, path: Dict, progress: LearningProgress, completion_rate: float, avg_score: float) -> List[str]:
        """生成进度建议"""
        recommendations = []
        
        if completion_rate < 0.3:
            recommendations.append("建议每天保持至少30分钟的学习时间")
        elif completion_rate > 0.7:
            recommendations.append("学习进度良好，继续保持！")
        
        if avg_score < 0.6:
            recommendations.append("建议复习已学内容，加强薄弱点")
        elif avg_score > 0.85:
            recommendations.append("掌握度优秀，可以尝试更有挑战性的内容")
        
        if progress.total_time_spent_minutes > 120 and completion_rate < 0.5:
            recommendations.append("建议调整学习方法，提高学习效率")
        
        return recommendations


def profile_time_budget_to_minutes(time_budget: str) -> int:
    """将时间预算字符串转换为分钟"""
    if "分钟" in time_budget:
        match = re.search(r'(\d+)\s*分钟', time_budget)
        return int(match.group(1)) if match else 30
    elif "小时" in time_budget:
        match = re.search(r'(\d+)\s*小时', time_budget)
        return int(match.group(1)) * 60 if match else 60
    return 45
