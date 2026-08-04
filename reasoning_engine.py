"""
Chain-of-Thought Reasoning Engine for DevMind IDE.
Provides structured reasoning capabilities for HermesAgent and other agents.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReasoningConfig:
    enabled: bool = True
    max_steps: int = 10
    style: str = "chain_of_thought"
    self_consistency: bool = False
    verify_reasoning: bool = False


@dataclass
class ReasoningStep:
    step_number: int
    thought: str
    evidence: str = ""
    confidence: float = 0.0


class ReasoningTrace:
    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.total_steps: int = 0

    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)
        self.total_steps += 1

    def to_dict(self) -> dict:
        return {
            "total_steps": self.total_steps,
            "steps": [
                {
                    "step_number": s.step_number,
                    "thought": s.thought,
                    "evidence": s.evidence,
                    "confidence": s.confidence,
                }
                for s in self.steps
            ],
        }

    def get_final_conclusion(self) -> str:
        if not self.steps:
            return ""
        return self.steps[-1].thought


class ReasoningEngine:
    def __init__(self, config: ReasoningConfig = None):
        self.config = config or ReasoningConfig()

    async def generate_reasoning(self, task, model: str = "") -> str:
        if not self.config.enabled:
            return ""

        trace = ReasoningTrace()
        steps = self._plan_reasoning_steps(task)

        for i, step_text in enumerate(steps):
            step = ReasoningStep(
                step_number=i + 1,
                thought=step_text,
                confidence=self._compute_confidence(step_text),
            )
            trace.add_step(step)

        return trace.to_dict()

    def _plan_reasoning_steps(self, task) -> List[str]:
        steps = []
        description = task.description or task.title or ""

        steps.append(f"Analyzing task: {description[:200]}")

        if "implement" in description.lower() or "code" in description.lower():
            steps.append("Identifying required implementation approach")
            steps.append("Planning code structure and dependencies")
        elif "fix" in description.lower() or "debug" in description.lower():
            steps.append("Identifying root cause of the issue")
            steps.append("Planning fix strategy")
        elif "review" in description.lower() or "analyze" in description.lower():
            steps.append("Examining codebase for relevant patterns")
            steps.append("Checking for potential issues")
        elif "test" in description.lower():
            steps.append("Identifying test scenarios")
            steps.append("Planning test coverage")
        else:
            steps.append("Breaking down task into sub-tasks")
            steps.append("Planning execution approach")

        steps.append("Executing planned approach")
        steps.append("Verifying results")

        return steps[: self.config.max_steps]

    def _compute_confidence(self, step_text: str) -> float:
        keywords = ["analyzing", "identifying", "planning", "executing", "verifying"]
        for kw in keywords:
            if kw in step_text.lower():
                return 0.8
        return 0.5

    async def self_consistency_check(self, reasoning: str, task) -> bool:
        if not self.config.self_consistency:
            return True
        if not reasoning:
            return False
        return len(reasoning) > 10

    def extract_reasoning_blocks(self, text: str) -> List[str]:
        pattern = r"<thinking>(.*?)</thinking>"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches

    def strip_reasoning(self, text: str) -> str:
        pattern = r"<thinking>.*?</thinking>"
        return re.sub(pattern, "", text, flags=re.DOTALL).strip()

    async def verify_reasoning(self, reasoning: str, evidence: str) -> bool:
        if not reasoning or not evidence:
            return False
        return len(reasoning.strip()) > 0 and len(evidence.strip()) > 0
