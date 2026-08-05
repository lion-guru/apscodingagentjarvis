"""
DevMind Agent Registry — tracks all agents, broadcasts status to Agent Town,
and provides agent-specific chat routing.

Provides:
  - GET /api/agent-town/agents → list all agents with status
  - GET /api/agent-town/activity → recent activity feed
  - POST /api/agent-town/chat → chat routed to best agent
  - WebSocket /ws/agent-town → real-time agent status + activity stream
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict


@dataclass
class AgentInfo:
    agent_id: str
    name: str
    emoji: str
    role: str
    status: str = "idle"  # idle, running, done, failed
    current_task: str = ""
    last_active: float = 0.0
    model: str = ""
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class ActivityEntry:
    id: str
    agent_id: str
    agent_name: str
    agent_emoji: str
    action: str  # started, completed, failed, chat
    task: str
    response: str = ""
    timestamp: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self):
        return asdict(self)


# ── Registry of all DevMind agents ──────────────────────────

AGENTS: Dict[str, AgentInfo] = {
    "planner": AgentInfo(
        agent_id="planner",
        name="Planner",
        emoji=" planning",
        role="Task Planner",
        model="gemini-2.5-flash",
        capabilities=["task_breakdown", "architecture", "scheduling"],
    ),
    "coder": AgentInfo(
        agent_id="coder",
        name="Coder",
        emoji="‍♂️",
        role="Code Generator",
        model="qwen2.5-coder:7b",
        capabilities=["code_generation", "refactoring", "debugging"],
    ),
    "reviewer": AgentInfo(
        agent_id="reviewer",
        name="Reviewer",
        emoji=" ",
        role="Code Reviewer",
        model="gemini-2.5-flash",
        capabilities=["code_review", "security_audit", "quality_check"],
    ),
    "healer": AgentInfo(
        agent_id="healer",
        name="Healer",
        emoji="️",
        role="Bug Fixer",
        model="llama-3.3-70b-versatile",
        capabilities=["bug_detection", "auto_fix", "error_recovery"],
    ),
    "researcher": AgentInfo(
        agent_id="researcher",
        name="Researcher",
        emoji=" ",
        role="Code Researcher",
        model="gemini-2.5-flash",
        capabilities=["codebase_exploration", "pattern_search", "documentation"],
    ),
    "architect": AgentInfo(
        agent_id="architect",
        name="Architect",
        emoji="️",
        role="System Architect",
        model="gemini-2.5-flash",
        capabilities=["system_design", "module_structure", "dependency_analysis"],
    ),
    "testRunner": AgentInfo(
        agent_id="testRunner",
        name="Test Runner",
        emoji="️",
        role="Test Executor",
        model="qwen2.5-coder:7b",
        capabilities=["test_execution", "coverage_analysis", "regression_check"],
    ),
    "deployer": AgentInfo(
        agent_id="deployer",
        name="Deployer",
        emoji="️",
        role="Deployment Agent",
        model="llama-3.3-70b-versatile",
        capabilities=["docker_build", "cloud_deploy", "health_check"],
    ),
    "monitor": AgentInfo(
        agent_id="monitor",
        name="Monitor",
        emoji="️",
        role="System Monitor",
        model="llama-3.1-8b-instant",
        capabilities=["resource_tracking", "alert_management", "log_analysis"],
    ),
    "hermes": AgentInfo(
        agent_id="hermes",
        name="Hermes",
        emoji="⚡",
        role="High-Speed Agent",
        model="llama-3.3-70b-versatile",
        capabilities=["reasoning", "tool_calling", "multi_step_planning"],
    ),
    "memory": AgentInfo(
        agent_id="memory",
        name="Memory",
        emoji=" ",
        role="Memory Manager",
        model="qwen2.5-coder:7b",
        capabilities=["context_retrieval", "knowledge_indexing", "session_management"],
    ),
    "linter": AgentInfo(
        agent_id="linter",
        name="Linter",
        emoji=" ",
        role="Code Quality",
        model="qwen2.5-coder:7b",
        capabilities=["lint_check", "format_enforce", "style_guide"],
    ),
}


# ── Smart Task Router ─────────────────────────────────────────

INTENT_PATTERNS = [
    (re.compile(r"review|code\s*review|audit|pr\s*review", re.I), "reviewer"),
    (re.compile(r"fix|bug|error|issue|crash|exception|debug|heal|repair", re.I), "healer"),
    (re.compile(r"plan|architect|design|system\s*design|api\s*design", re.I), "planner"),
    (re.compile(r"test|spec|coverage|unit\s*test|integration\s*test", re.I), "testRunner"),
    (re.compile(r"deploy|docker|ci/cd|build|release|ship", re.I), "deployer"),
    (re.compile(r"search|find|grep|look\s*for|research|explore", re.I), "researcher"),
    (re.compile(r"lint|format|style|clean\s*code|prettier|eslint", re.I), "linter"),
    (re.compile(r"remember|memory|context|recall|what\s*did", re.I), "memory"),
    (re.compile(r"monitor|status|health|uptime|performance|metrics", re.I), "monitor"),
    (re.compile(r"write|create|implement|build|code|function|class|module|component", re.I), "coder"),
    (re.compile(r"refactor|optimize|improve|clean\s*up|restructure", re.I), "architect"),
]


def route_task(description: str) -> str:
    """Route a task description to the best agent ID."""
    for pattern, agent_id in INTENT_PATTERNS:
        if pattern.search(description):
            return agent_id
    return "coder"


# ── Activity Feed ────────────────────────────────────────────

_activity: List[ActivityEntry] = []
_activity_counter = 0


def _next_id() -> str:
    global _activity_counter
    _activity_counter += 1
    return f"act_{int(time.time())}_{_activity_counter}"


def add_activity(agent_id: str, action: str, task: str, response: str = "", duration_ms: float = 0.0):
    """Add an entry to the activity feed and broadcast."""
    agent = AGENTS.get(agent_id)
    entry = ActivityEntry(
        id=_next_id(),
        agent_id=agent_id,
        agent_name=agent.name if agent else agent_id,
        agent_emoji=agent.emoji if agent else " ",
        action=action,
        task=task,
        response=response,
        timestamp=time.time(),
        duration_ms=duration_ms,
    )
    _activity.insert(0, entry)
    if len(_activity) > 50:
        _activity.pop()
    # Broadcast activity update
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_broadcast_activity(entry))
    except RuntimeError:
        pass


def get_activity(limit: int = 30) -> List[dict]:
    """Return recent activity entries."""
    return [e.to_dict() for e in _activity[:limit]]


# ── WebSocket connections ──────────────────────────────────

_ws_clients: Set = set()


def get_all_agents() -> List[dict]:
    """Return all agents as dicts."""
    return [a.to_dict() for a in AGENTS.values()]


def get_agent(agent_id: str) -> Optional[dict]:
    """Return a single agent by ID."""
    agent = AGENTS.get(agent_id)
    return agent.to_dict() if agent else None


def update_agent_status(agent_id: str, status: str, task: str = ""):
    """Update agent status and broadcast to WebSocket clients."""
    agent = AGENTS.get(agent_id)
    if not agent:
        return
    agent.status = status
    agent.current_task = task
    agent.last_active = time.time()
    # Broadcast in background
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_broadcast_status())
    except RuntimeError:
        pass


async def _broadcast_status():
    """Send current agent status to all connected WebSocket clients."""
    if not _ws_clients:
        return
    data = json.dumps({
        "type": "agent_status",
        "agents": get_all_agents(),
        "timestamp": time.time(),
    })
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


async def _broadcast_activity(entry: ActivityEntry):
    """Send activity entry to all connected WebSocket clients."""
    if not _ws_clients:
        return
    data = json.dumps({
        "type": "activity",
        "entry": entry.to_dict(),
        "timestamp": time.time(),
    })
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


def register_ws_client(ws):
    """Register a WebSocket client for broadcasts."""
    _ws_clients.add(ws)


def unregister_ws_client(ws):
    """Unregister a WebSocket client."""
    _ws_clients.discard(ws)
