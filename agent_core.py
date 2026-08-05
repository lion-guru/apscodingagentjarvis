import asyncio
import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"
    CANCELLED = "cancelled"


class ToolResult:
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error}


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    agent_role: str = "general"
    subtasks: List["Task"] = field(default_factory=list)
    parent_task_id: str = ""
    status: AgentStatus = AgentStatus.PENDING
    result: Optional[ToolResult] = None
    tool_calls: List[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    requires_approval: bool = False
    approval_decision: Optional[bool] = None
    error: str = ""
    reasoning_trace: Optional[str] = None
    attention_config: Optional[dict] = None
    stream_channels: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: List[dict] = field(default_factory=list)


class SubagentPool:
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def submit(self, agent: "Agent", task: Task) -> Task:
        async with self._semaphore:
            if task.id in self._active_tasks:
                return task
            coro = self._run_agent(agent, task)
            task_obj = asyncio.create_task(coro)
            self._active_tasks[task.id] = task_obj
            try:
                await task_obj
            except asyncio.CancelledError:
                task.status = AgentStatus.CANCELLED
            except Exception as e:
                task.status = AgentStatus.FAILED
                task.error = str(e)
            finally:
                self._active_tasks.pop(task.id, None)
            return task

    async def _run_agent(self, agent: "Agent", task: Task) -> None:
        task.status = AgentStatus.RUNNING
        result = await agent.execute(task)
        task.result = result
        task.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
        task.completed_at = time.time()

    def get_active_count(self) -> int:
        return len(self._active_tasks)

    def cancel_all(self):
        for task_id, task_obj in list(self._active_tasks.items()):
            task_obj.cancel()
        self._active_tasks.clear()


class Agent:
    def __init__(
        self,
        role: str,
        model: str = "gemma3:1b",
        context_window: int = 4096,
        max_subagents: int = 4,
    ):
        self.role = role
        self.model = model
        self.context_window = context_window
        self.subagent_pool = SubagentPool(max_concurrent=max_subagents)
        self.messages: List[AgentMessage] = []
        self.tools: Dict[str, Callable] = {}
        self._running = False

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def register_tools(self, tools: Dict[str, Callable]):
        self.tools.update(tools)

    async def execute(self, task: Task) -> ToolResult:
        self._running = True
        try:
            self._add_message("system", f"Agent role: {self.role}. Model: {self.model}")
            self._add_message("user", task.description)
            result = await self._run_task(task)
            return result
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
        finally:
            self._running = False

    async def _run_task(self, task: Task) -> ToolResult:
        if task.subtasks:
            return await self._execute_subtasks(task)
        return await self._execute_single_task(task)

    async def _execute_single_task(self, task: Task) -> ToolResult:
        tool_name = task.agent_role
        if tool_name in self.tools:
            try:
                output = await self._call_tool(tool_name, task)
                return ToolResult(success=True, output=output)
            except Exception as e:
                return ToolResult(success=False, output="", error=str(e))
        if self.tools:
            tool_name = next(iter(self.tools))
            try:
                output = await self._call_tool(tool_name, task)
                return ToolResult(success=True, output=output)
            except Exception as e:
                return ToolResult(success=False, output="", error=str(e))
        return ToolResult(
            success=False,
            output="",
            error=f"No tools registered for agent '{self.role}'",
        )

    async def _execute_subtasks(self, task: Task) -> ToolResult:
        results = []
        subtask_objs = [Task(**{**t.__dict__}) if isinstance(t, Task) else t for t in task.subtasks]
        for subtask in subtask_objs:
            subtask.parent_task_id = task.id
            result = await self.subagent_pool.submit(self, subtask)
            results.append(result)
        all_success = all(r.success for r in results)
        combined_output = "\n".join(
            f"[{r.status.value}] {r.output}" for r in results if r.output
        )
        combined_error = "\n".join(r.error for r in results if r.error)
        return ToolResult(
            success=all_success,
            output=combined_output,
            error=combined_error,
        )

    async def _call_tool(self, tool_name: str, task: Task) -> str:
        tool = self.tools[tool_name]
        if asyncio.iscoroutinefunction(tool):
            return await tool(task)
        return tool(task)

    def _add_message(self, role: str, content: str, tool_calls: List[dict] = None):
        self.messages.append(AgentMessage(role=role, content=content, tool_calls=tool_calls or []))

    def get_context(self) -> List[AgentMessage]:
        return self.messages[-20:]

    def clear_context(self):
        self.messages.clear()

    @property
    def is_running(self) -> bool:
        return self._running


class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.approval_queue: List[Task] = []
        self.steering_rules: List[str] = []

    def register_agent(self, agent: Agent):
        self.agents[agent.role] = agent

    def create_task(self, title: str, description: str, agent_role: str = "general", requires_approval: bool = False) -> Task:
        task = Task(title=title, description=description, agent_role=agent_role, requires_approval=requires_approval)
        self.tasks[task.id] = task
        if requires_approval:
            self.approval_queue.append(task)
        return task

    async def execute_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        agent = self.agents.get(task.agent_role)
        if not agent:
            agent = self.agents.get("general")
        if not agent:
            task.status = AgentStatus.FAILED
            task.error = "No agent available"
            return task
        # Broadcast agent running status to Agent Town
        try:
            from agent_town_bridge import update_agent_status
            update_agent_status(task.agent_role, "running", task.title)
        except Exception:
            pass
        result = await agent.execute(task)
        task.result = result
        task.status = AgentStatus.COMPLETED if result.success else AgentStatus.FAILED
        task.completed_at = time.time()
        # Broadcast agent done/failed status to Agent Town
        try:
            from agent_town_bridge import update_agent_status
            status = "done" if result.success else "failed"
            update_agent_status(task.agent_role, status, task.title)
        except Exception:
            pass
        return task

    def approve_task(self, task_id: str, approved: bool) -> bool:
        task = self.tasks.get(task_id)
        if not task or task_id not in [t.id for t in self.approval_queue]:
            return False
        task.approval_decision = approved
        self.approval_queue = [t for t in self.approval_queue if t.id != task_id]
        if approved:
            task.requires_approval = False
        return approved

    def add_steering_rule(self, rule: str):
        self.steering_rules.append(rule)

    def get_active_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status in (AgentStatus.PENDING, AgentStatus.RUNNING)]

    def get_task_status(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def set_moe_router(self, router) -> None:
        self._moe_router = router

    def get_expert_status(self) -> dict:
        if hasattr(self, "_moe_router") and self._moe_router is not None:
            return self._moe_router.get_expert_status()
        return {"status": "ok", "experts": [], "total_tasks": len(self.tasks)}


_orchestrator = AgentOrchestrator()


def _get_orchestrator() -> AgentOrchestrator:
    return _orchestrator


async def execute_agent(title: str, description: str, agent_role: str = "general", requires_approval: bool = False) -> dict:
    task = _orchestrator.create_task(title=title, description=description, agent_role=agent_role, requires_approval=requires_approval)
    result_task = await _orchestrator.execute_task(task.id)
    return {
        "task_id": result_task.id,
        "status": result_task.status.value,
        "title": result_task.title,
        "result": result_task.result.to_dict() if result_task.result else None,
        "error": result_task.error,
    }


async def delegate_subagent(parent_task_id: str, subtask_title: str, subtask_description: str, agent_role: str = "general") -> dict:
    parent_task = _orchestrator.tasks.get(parent_task_id)
    if not parent_task:
        return {"status": "error", "message": f"Parent task {parent_task_id} not found"}
    subtask = Task(title=subtask_title, description=subtask_description, agent_role=agent_role)
    parent_task.subtasks.append(subtask)
    _orchestrator.tasks[subtask.id] = subtask
    result = await _orchestrator.execute_task(subtask.id)
    return {
        "subtask_id": result.id,
        "parent_task_id": parent_task_id,
        "status": result.status.value,
        "result": result.result.to_dict() if result.result else None,
    }


async def approve_operation(task_id: str, approved: bool) -> dict:
    result = _orchestrator.approve_task(task_id, approved)
    return {"task_id": task_id, "approved": approved, "success": result}


async def steer_agent(rules: list) -> dict:
    for rule in rules:
        _orchestrator.add_steering_rule(rule)
    return {"status": "ok", "rules_added": len(rules), "total_rules": len(_orchestrator.steering_rules)}


async def get_agent_status(task_id: str) -> dict:
    task = _orchestrator.get_task_status(task_id)
    if not task:
        return {"status": "error", "message": f"Task {task_id} not found"}
    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status.value,
        "agent_role": task.agent_role,
        "requires_approval": task.requires_approval,
        "approval_decision": task.approval_decision,
        "error": task.error,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }


async def get_active_tasks() -> dict:
    tasks = _orchestrator.get_active_tasks()
    return {
        "status": "ok",
        "active_tasks": [
            {
                "task_id": t.id,
                "title": t.title,
                "status": t.status.value,
                "agent_role": t.agent_role,
                "requires_approval": t.requires_approval,
            }
            for t in tasks
        ],
    }
