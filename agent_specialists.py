import asyncio
from typing import Any, Dict, List, Optional
from agent_core import Agent, Task, ToolResult
from hermes_agent import HermesAgent


class PlannerAgent(Agent):
    def __init__(self, model: str = "gemma3:1b"):
        super().__init__(role="planner", model=model)
        self.register_tool("plan_task", self.plan_task)
        self.register_tool("decompose", self.decompose_task)

    async def plan_task(self, task: Task) -> str:
        lines = [
            f"# Plan for: {task.title}",
            f"Description: {task.description}",
            "",
            "## Steps:",
            "1. Analyze the current codebase state",
            "2. Identify files that need changes",
            "3. Plan the implementation approach",
            "4. Execute changes incrementally",
            "5. Verify with tests and linter",
            "",
            "## Risk Assessment:",
            "- Low risk: documentation or config changes",
            "- Medium risk: new feature implementation",
            "- High risk: architecture changes or deletions",
        ]
        return "\n".join(lines)

    async def decompose_task(self, task: Task) -> str:
        subtasks = []
        for i, subtask in enumerate(task.subtasks, 1):
            subtasks.append(f"{i}. [{subtask.agent_role}] {subtask.title}")
        return "\n".join(subtasks) if subtasks else "No subtasks defined"


class CoderAgent(Agent):
    def __init__(self, model: str = "gemma3:1b"):
        super().__init__(role="coder", model=model)
        self.register_tool("inline_edit", self.inline_edit)
        self.register_tool("create_file", self.create_file)
        self.register_tool("refactor", self.refactor)

    async def inline_edit(self, task: Task) -> str:
        return f"[Coder] Applied inline edit for: {task.title}"

    async def create_file(self, task: Task) -> str:
        return f"[Coder] Created new file: {task.title}"

    async def refactor(self, task: Task) -> str:
        return f"[Coder] Refactored: {task.title}"


class ReviewerAgent(Agent):
    def __init__(self, model: str = "gemma3:1b"):
        super().__init__(role="reviewer", model=model)
        self.register_tool("lint_check", self.lint_check)
        self.register_tool("type_check", self.type_check)
        self.register_tool("test_run", self.test_run)

    async def lint_check(self, task: Task) -> str:
        return "[Reviewer] Lint check passed"

    async def type_check(self, task: Task) -> str:
        return "[Reviewer] Type check passed"

    async def test_run(self, task: Task) -> str:
        return "[Reviewer] All tests passed"


class HealerAgent(Agent):
    def __init__(self, model: str = "gemma3:1b"):
        super().__init__(role="healer", model=model)
        self.register_tool("auto_fix", self.auto_fix)
        self.register_tool("rollback", self.rollback)

    async def auto_fix(self, task: Task) -> str:
        return f"[Healer] Auto-fixed: {task.title}"

    async def rollback(self, task: Task) -> str:
        return f"[Healer] Rolled back: {task.title}"


class GeneralAgent(Agent):
    def __init__(self, model: str = "gemma3:1b"):
        super().__init__(role="general", model=model)
        self.register_tool("execute_command", self.execute_command)
        self.register_tool("read_file", self.read_file)
        self.register_tool("write_file", self.write_file)

    async def execute_command(self, task: Task) -> str:
        return f"[General] Executed command: {task.title}"

    async def read_file(self, task: Task) -> str:
        return f"[General] Read file: {task.title}"

    async def write_file(self, task: Task) -> str:
        return f"[General] Wrote file: {task.title}"


def create_default_agents() -> Dict[str, Agent]:
    return {
        "planner": PlannerAgent(),
        "coder": CoderAgent(),
        "reviewer": ReviewerAgent(),
        "healer": HealerAgent(),
        "general": GeneralAgent(),
        "hermes": HermesAgent(),
        "hermes_fast": HermesAgent(model="gemma3:1b", reasoning_depth=1, tool_calling_mode="auto", max_execution_steps=10),
        "hermes_deep": HermesAgent(model="gemma3:1b", reasoning_depth=3, tool_calling_mode="explicit", max_execution_steps=30),
    }