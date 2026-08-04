"""
Mixture of Experts (MoE) Router for DevMind IDE.
Routes tasks to the optimal specialist agent based on task type, complexity, and model capability.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent_core import Task


@dataclass
class ExpertProfile:
    expert_name: str
    model: str = "gemma3:1b"
    capabilities: List[str] = field(default_factory=list)
    speed_tier: str = "medium"
    cost_per_token: float = 0.0


class TaskClassifier:
    def __init__(self):
        self._code_patterns = [
            r"\bcode\b", r"\bimplement\b", r"\bfix\b", r"\bbug\b",
            r"\brefactor\b", r"\bedit\b", r"\bwrite\b.*\bfile\b",
            r"\bfunction\b", r"\bclass\b", r"\bmethod\b", r"\bpython\b",
            r"\bjavascript\b", r"\btypescript\b", r"\bjava\b", r"\bc\+\+\b",
        ]
        self._reasoning_patterns = [
            r"\bwhy\b", r"\bhow\b", r"\bexplain\b", r"\banalyze\b",
            r"\breason\b", r"\bthink\b", r"\bunderstand\b", r"\bconcept\b",
        ]
        self._search_patterns = [
            r"\bsearch\b", r"\bfind\b", r"\blook\b", r"\bquery\b",
            r"\blocate\b", r"\bgrep\b", r"\bwhere\b",
        ]
        self._creative_patterns = [
            r"\bwrite\b", r"\bcreate\b", r"\bdesign\b", r"\bbuild\b",
            r"\bgenerate\b", r"\bplan\b", r"\barchitect\b",
        ]

    def classify(self, task_description: str) -> dict:
        text = task_description.lower()
        scores = {
            "type": "general",
            "complexity": "low",
            "requires_vision": False,
        }

        code_score = sum(1 for p in self._code_patterns if re.search(p, text))
        reasoning_score = sum(1 for p in self._reasoning_patterns if re.search(p, text))
        search_score = sum(1 for p in self._search_patterns if re.search(p, text))
        creative_score = sum(1 for p in self._creative_patterns if re.search(p, text))

        max_score = max(code_score, reasoning_score, search_score, creative_score, 1)

        if code_score == max_score:
            scores["type"] = "code"
        elif reasoning_score == max_score:
            scores["type"] = "reasoning"
        elif search_score == max_score:
            scores["type"] = "search"
        elif creative_score == max_score:
            scores["type"] = "creative"

        word_count = len(text.split())
        if word_count > 50:
            scores["complexity"] = "high"
        elif word_count > 20:
            scores["complexity"] = "medium"
        else:
            scores["complexity"] = "low"

        return scores

    def extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        stop_words = {"the", "this", "that", "with", "from", "have", "been", "were", "their", "which"}
        return [w for w in words if w not in stop_words][:10]


class MoEPolicy:
    def __init__(self):
        self._weights = {
            "code": {"coder": 0.4, "planner": 0.3, "general": 0.3},
            "reasoning": {"planner": 0.4, "reviewer": 0.3, "general": 0.3},
            "search": {"reviewer": 0.4, "general": 0.6},
            "creative": {"planner": 0.5, "general": 0.5},
            "general": {"general": 1.0},
        }

    def select_expert(self, classification: dict, experts: List[ExpertProfile]) -> ExpertProfile:
        task_type = classification.get("type", "general")
        complexity = classification.get("complexity", "low")
        weights = self._weights.get(task_type, {"general": 1.0})

        for expert in experts:
            if expert.expert_name in weights:
                return expert

        for expert in experts:
            if expert.expert_name == "general":
                return expert

        return experts[0] if experts else ExpertProfile(expert_name="general")

    def balance_load(self, experts: List[ExpertProfile]) -> dict:
        total = len(experts)
        if total == 0:
            return {}
        weight = 1.0 / total
        return {e.expert_name: weight for e in experts}


class MoERouter:
    def __init__(self, experts: Dict[str, ExpertProfile] = None):
        self.experts = experts or {}
        self.classifier = TaskClassifier()
        self.policy = MoEPolicy()
        self._routing_history: List[dict] = []

    def route_task(self, task: Task) -> str:
        classification = self.classifier.classify(task.description or task.title or "")
        expert = self.policy.select_expert(classification, list(self.experts.values()))

        self._routing_history.append({
            "task_id": task.id,
            "task_type": classification["type"],
            "complexity": classification["complexity"],
            "routed_to": expert.expert_name,
        })

        return expert.expert_name

    def route_model(self, task_type: str, requirements: dict = None) -> str:
        requirements = requirements or {}
        if task_type == "code":
            return requirements.get("model", "gemma3:1b")
        elif task_type == "reasoning":
            return requirements.get("model", "gemma3:1b")
        elif task_type == "search":
            return requirements.get("model", "gemma3:1b")
        return requirements.get("model", "gemma3:1b")

    def add_expert(self, expert: ExpertProfile) -> None:
        self.experts[expert.expert_name] = expert

    def remove_expert(self, expert_name: str) -> bool:
        if expert_name in self.experts:
            del self.experts[expert_name]
            return True
        return False

    def get_expert_status(self) -> dict:
        return {
            "status": "ok",
            "experts": [
                {
                    "name": e.expert_name,
                    "model": e.model,
                    "capabilities": e.capabilities,
                    "speed_tier": e.speed_tier,
                }
                for e in self.experts.values()
            ],
            "total_experts": len(self.experts),
            "total_routes": len(self._routing_history),
        }

    def get_routing_history(self, limit: int = 50) -> List[dict]:
        return self._routing_history[-limit:]
