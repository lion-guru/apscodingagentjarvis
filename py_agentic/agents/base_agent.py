"""
Base Agent - Abstract base class for all specialized agents.

Each agent has:
  - A role description
  - A set of tools (shell, filesystem, ollama)
  - A process_task() method that handles tasks of its type
  - Async support for concurrent execution

Agents are designed to be composable - they can be used standalone
or orchestrated by the main Orchestrator.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import sys
import os
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from tools.shell import ShellTool
from tools.filesystem import FilesystemTool
from ollama_client import OllamaClient


@dataclass
class AgentResult:
    """Result of an agent task execution."""
    agent_id: str
    task_type: str
    success: bool
    description: str
    changes_made: list = field(default_factory=list)
    duration_sec: float = 0.0
    error: Optional[str] = None
    ai_insight: Optional[str] = None


class BaseAgent:
    """Abstract base class for all agents."""

    def __init__(self, agent_id: str, name: str, role: str, description: str,
                 tools: list, shell: ShellTool, fs: FilesystemTool,
                 ollama: Optional[OllamaClient] = None, config: Optional[dict] = None):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.description = description
        self.tools = tools
        self.shell = shell
        self.fs = fs
        self.ollama = ollama
        self.config = config or {}
        self.project_root = shell.project_root

    async def process_task(self, task: Dict[str, Any]) -> AgentResult:
        """
        Process a single task. Override in subclasses.

        Args:
            task: Task dict with 'type', 'priority', 'desc', 'detail'

        Returns:
            AgentResult with execution details
        """
        start = time.time()
        try:
            result = await self._handle_task(task)
            return AgentResult(
                agent_id=self.agent_id,
                task_type=task.get('type', 'unknown'),
                success=True,
                description=task.get('desc', ''),
                changes_made=result.get('changes', []),
                duration_sec=time.time() - start,
                ai_insight=result.get('ai_insight')
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_type=task.get('type', 'unknown'),
                success=False,
                description=task.get('desc', ''),
                duration_sec=time.time() - start,
                error=str(e)
            )

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to handle specific task types."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _handle_task")

    def can_handle(self, task_type: str) -> bool:
        """Return True if this agent can handle the given task type."""
        return task_type in self._handled_types()

    def _handled_types(self) -> List[str]:
        """Return list of task types this agent handles. Override in subclasses."""
        return []

    async def _ai_reason(self, prompt: str, system: str = '') -> str:
        """Use Ollama for AI reasoning if available."""
        if self.ollama and self.ollama.is_available():
            try:
                return await asyncio.to_thread(
                    self.ollama.generate, prompt, system, 4096
                )
            except Exception:
                return ''
        return ''

    async def _chat(self, messages: list) -> str:
        """Use Ollama chat if available."""
        if self.ollama and self.ollama.is_available():
            try:
                return await asyncio.to_thread(self.ollama.chat, messages)
            except Exception:
                return ''
        return ''

    def _log(self, message: str) -> None:
        """Log a message with agent prefix."""
        print(f"[{self.agent_id}] {message}")
