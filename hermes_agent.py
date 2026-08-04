"""
Hermes High-Speed Execution Agent for DevMind IDE.
Provides reasoning, tool calling, MoE routing, and high-speed execution.
"""
import asyncio
from typing import Any, Dict, List, Optional

from agent_core import Agent, Task, ToolResult, AgentStatus
from reasoning_engine import ReasoningEngine, ReasoningConfig


class HermesToolExecutor:
    def __init__(self, tool_registry: Dict[str, Any] = None):
        self.tool_registry = tool_registry or {}
        self.max_retries = 3
        self.default_timeout_s = 30

    async def execute_with_retry(self, tool_name: str, params: dict, max_retries: int = None) -> ToolResult:
        retries = max_retries or self.max_retries
        last_error = None
        for attempt in range(retries):
            try:
                result = await self.execute_with_timeout(tool_name, params)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
            await asyncio.sleep(0.1 * (attempt + 1))
        return ToolResult(success=False, output="", error=f"Failed after {retries} retries: {last_error}")

    async def execute_with_timeout(self, tool_name: str, params: dict, timeout_s: float = None) -> ToolResult:
        timeout = timeout_s or self.default_timeout_s
        if tool_name not in self.tool_registry:
            return ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")
        try:
            tool_func = self.tool_registry[tool_name]
            if asyncio.iscoroutinefunction(tool_func):
                result = await asyncio.wait_for(tool_func(**params), timeout=timeout)
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, lambda: tool_func(**params))
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=str(result))
        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error=f"Tool {tool_name} timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Tool {tool_name} error: {e}")

    def validate_tool_params(self, tool_name: str, params: dict) -> bool:
        if tool_name not in self.tool_registry:
            return False
        tool = self.tool_registry[tool_name]
        if hasattr(tool, "params_schema") and tool.params_schema:
            for key in tool.params_schema.get("required", []):
                if key not in params:
                    return False
        return True


class HermesAgent(Agent):
    def __init__(
        self,
        model: str = "gemma3:1b",
        reasoning_depth: int = 1,
        tool_calling_mode: str = "auto",
        max_execution_steps: int = 20,
    ):
        super().__init__(role="hermes", model=model)
        self.reasoning_depth = reasoning_depth
        self.tool_calling_mode = tool_calling_mode
        self.max_execution_steps = max_execution_steps
        self.reasoning_engine = ReasoningEngine(
            ReasoningConfig(enabled=True, max_steps=reasoning_depth * 3)
        )
        self._tool_executor = HermesToolExecutor()
        self._moe_router = None

    def set_moe_router(self, router) -> None:
        self._moe_router = router

    async def execute(self, task: Task) -> ToolResult:
        self._running = True
        try:
            self._add_message("system", f"Hermes Agent role: {self.role}. Model: {self.model}")
            self._add_message("user", task.description)

            reasoning_result = await self._reasoning_step(task)
            if reasoning_result:
                task.reasoning_trace = str(reasoning_result)

            result = await self._tool_execution_loop(task, self.max_execution_steps)
            return result
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
        finally:
            self._running = False

    async def _reasoning_step(self, task: Task) -> dict:
        if self.reasoning_depth == 0:
            return {}
        try:
            reasoning = await self.reasoning_engine.generate_reasoning(task, self.model)
            return reasoning
        except Exception:
            return {}

    async def _tool_execution_loop(self, task: Task, max_steps: int) -> ToolResult:
        for step in range(max_steps):
            if not self._running:
                return ToolResult(success=False, output="", error="Execution cancelled")

            tool_name = self._select_tool(task, step)
            if not tool_name:
                break

            params = self._build_params(task, tool_name)
            result = await self._tool_executor.execute_with_retry(tool_name, params)

            if result.success:
                self._add_message("tool", f"[{tool_name}] {result.output}")
                if self._is_task_complete(task, result):
                    task.status = AgentStatus.COMPLETED
                    return result
            else:
                self._add_message("tool", f"[{tool_name}] ERROR: {result.error}")
                if step >= max_steps - 1:
                    task.status = AgentStatus.FAILED
                    task.error = result.error
                    return result

        task.status = AgentStatus.COMPLETED
        return ToolResult(success=True, output="Execution completed")

    def _select_tool(self, task: Task, step: int) -> Optional[str]:
        if self.tool_calling_mode == "none":
            return None
        if step == 0 and self.tool_calling_mode == "auto":
            return task.agent_role if task.agent_role in self.tools else (next(iter(self.tools)) if self.tools else None)
        if self.tools:
            return next(iter(self.tools))
        return None

    def _build_params(self, task: Task, tool_name: str) -> dict:
        return {"task": task}

    def _is_task_complete(self, task: Task, result: ToolResult) -> bool:
        return result.success and not result.error

    async def _moe_route(self, task: Task) -> str:
        if self._moe_router is None:
            return self.role
        try:
            return self._moe_router.route_task(task)
        except Exception:
            return self.role


def create_hermes_agents() -> Dict[str, Agent]:
    return {
        "hermes": HermesAgent(model="gemma3:1b", reasoning_depth=2, tool_calling_mode="auto", max_execution_steps=20),
        "hermes_fast": HermesAgent(model="gemma3:1b", reasoning_depth=1, tool_calling_mode="auto", max_execution_steps=10),
        "hermes_deep": HermesAgent(model="gemma3:1b", reasoning_depth=3, tool_calling_mode="explicit", max_execution_steps=30),
    }
