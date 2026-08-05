"""
DevMind Agent Command Center
Central hub for managing AI agent commands, sub-agent spawning, and agentic workflows.
Inspired by Windsurf's agent commands and Trae's agent system.
Integrates with agent_core.py for multi-agent orchestration.
"""
import os
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from typing import Callable, Any

from agent_core import Task, AgentStatus, _orchestrator
import hermes_agent
import moe_router
import multimodal_engine
import stream_manager
import reasoning_engine

COMMANDS_DIR = Path.home() / ".devmind" / "commands"
SESSIONS_DIR = Path.home() / ".devmind" / "sessions"
AGENTS_DIR = Path.home() / ".devmind" / "agents"


class AgentCommandCenter:
    def __init__(self):
        COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.active_sessions = {}
        self.command_history = []
        self.orchestrator = _orchestrator

    def register_command(self, name: str, description: str, handler: Callable,
                         params_schema: dict = None, subcommands: list = None):
        cmd = {
            "name": name,
            "description": description,
            "handler": handler.__name__ if hasattr(handler, "__name__") else str(handler),
            "params_schema": params_schema or {},
            "subcommands": subcommands or [],
            "created_at": datetime.now().isoformat()
        }
        cmd_file = COMMANDS_DIR / f"{name}.json"
        cmd_file.write_text(json.dumps(cmd, indent=2, default=str), encoding="utf-8")
        return cmd

    def execute_command(self, name: str, params: dict = None) -> dict:
        cmd_file = COMMANDS_DIR / f"{name}.json"
        if not cmd_file.exists():
            return {"status": "error", "error": f"Command '{name}' not found"}

        cmd = json.loads(cmd_file.read_text(encoding="utf-8"))
        self.command_history.append({
            "command": name,
            "params": params,
            "timestamp": datetime.now().isoformat()
        })
        return {"status": "ok", "command": name, "result": f"Command '{name}' executed with params: {params}"}

    def spawn_sub_agent(self, name: str, instruction: str, model: str = "auto",
                        sub_tools: list = None, background: bool = False) -> dict:
        session_id = str(uuid.uuid4())[:8]
        agent = {
            "id": session_id,
            "name": name,
            "instruction": instruction,
            "model": model,
            "sub_tools": sub_tools or [],
            "background": background,
            "status": "running" if not background else "queued",
            "created_at": datetime.now().isoformat(),
            "progress": 0
        }
        agent_file = AGENTS_DIR / f"{session_id}.json"
        agent_file.write_text(json.dumps(agent, indent=2, default=str), encoding="utf-8")
        self.active_sessions[session_id] = agent
        return {"status": "ok", "agent_id": session_id, "agent": agent}

    def spawn_agent(self, name: str, instruction: str = "", model: str = "auto") -> dict:
        return self.spawn_sub_agent(name, instruction, model)

    def update_agent(self, agent_id: str, status: str, task: str = None) -> dict:
        agent_file = AGENTS_DIR / f"{agent_id}.json"
        if not agent_file.exists():
            return {"status": "error", "error": f"Agent '{agent_id}' not found"}
        try:
            agent = json.loads(agent_file.read_text(encoding="utf-8"))
            agent["status"] = status
            if task is not None:
                agent["instruction"] = task
            agent["updated_at"] = datetime.now().isoformat()
            agent_file.write_text(json.dumps(agent, indent=2, default=str), encoding="utf-8")
            self.active_sessions[agent_id] = agent
            return {"status": "ok", "agent_id": agent_id, "agent": agent}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def list_agents(self) -> list[dict]:
        agents = []
        if AGENTS_DIR.exists():
            for f in AGENTS_DIR.glob("*.json"):
                try:
                    agents.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return agents

    def get_agent_status(self, agent_id: str) -> dict:
        agent_file = AGENTS_DIR / f"{agent_id}.json"
        if not agent_file.exists():
            return {"status": "error", "error": f"Agent '{agent_id}' not found"}
        return json.loads(agent_file.read_text(encoding="utf-8"))

    def list_commands(self) -> list[dict]:
        commands = []
        if COMMANDS_DIR.exists():
            for f in COMMANDS_DIR.glob("*.json"):
                try:
                    commands.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        return commands

    def save_session(self, session_name: str, messages: list, artifacts: list = None,
                     context: dict = None) -> dict:
        session = {
            "name": session_name,
            "messages": messages,
            "artifacts": artifacts or [],
            "context": context or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        session_file = SESSIONS_DIR / f"{session_name}.json"
        session_file.write_text(json.dumps(session, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "session_name": session_name}

    def load_session(self, session_name: str) -> dict:
        session_file = SESSIONS_DIR / f"{session_name}.json"
        if not session_file.exists():
            return {"status": "error", "error": f"Session '{session_name}' not found"}
        return json.loads(session_file.read_text(encoding="utf-8"))

    def list_sessions(self) -> list[dict]:
        sessions = []
        if SESSIONS_DIR.exists():
            for f in SESSIONS_DIR.glob("*.json"):
                try:
                    s = json.loads(f.read_text(encoding="utf-8"))
                    sessions.append({
                        "name": s.get("name", f.stem),
                        "created_at": s.get("created_at", ""),
                        "message_count": len(s.get("messages", []))
                    })
                except Exception:
                    pass
        return sessions

    def run_agentic_loop(self, task: str, max_iterations: int = 10) -> dict:
        steps = []
        for i in range(max_iterations):
            step = {
                "iteration": i + 1,
                "task": task,
                "action": f"analyze_step_{i + 1}",
                "timestamp": datetime.now().isoformat()
            }
            steps.append(step)
        return {
            "status": "ok",
            "task": task,
            "iterations_completed": len(steps),
            "steps": steps
        }

    async def execute_agent_task(self, title: str, description: str, agent_role: str = "general",
                                  requires_approval: bool = False) -> dict:
        """Execute an agent task using the agent_core orchestrator."""
        task = self.orchestrator.create_task(
            title=title, description=description, agent_role=agent_role,
            requires_approval=requires_approval
        )
        result_task = await self.orchestrator.execute_task(task.id)
        return {
            "task_id": result_task.id,
            "status": result_task.status.value,
            "title": result_task.title,
            "result": result_task.result.to_dict() if result_task.result else None,
            "error": result_task.error,
        }

    async def delegate_to_subagent(self, parent_task_id: str, subtask_title: str,
                                    subtask_description: str, agent_role: str = "general") -> dict:
        """Delegate a subtask to a specialized subagent."""
        parent_task = self.orchestrator.tasks.get(parent_task_id)
        if not parent_task:
            return {"status": "error", "message": f"Parent task {parent_task_id} not found"}
        subtask = Task(title=subtask_title, description=subtask_description, agent_role=agent_role)
        parent_task.subtasks.append(subtask)
        result = await self.orchestrator.execute_task(subtask.id)
        return {
            "subtask_id": result.id,
            "parent_task_id": parent_task_id,
            "status": result.status.value,
            "result": result.result.to_dict() if result.result else None,
        }

    def get_active_tasks(self) -> list[dict]:
        """Get all active (pending/running) agent tasks."""
        tasks = self.orchestrator.get_active_tasks()
        return [
            {
                "task_id": t.id,
                "title": t.title,
                "status": t.status.value,
                "agent_role": t.agent_role,
                "requires_approval": t.requires_approval,
            }
            for t in tasks
        ]

    def add_steering_rule(self, rule: str) -> dict:
        """Add a steering rule to guide agent behavior."""
        self.orchestrator.add_steering_rule(rule)
        return {"status": "ok", "rule": rule, "total_rules": len(self.orchestrator.steering_rules)}

    def approve_task(self, task_id: str, approved: bool) -> dict:
        """Approve or deny a destructive operation."""
        result = self.orchestrator.approve_task(task_id, approved)
        return {"task_id": task_id, "approved": approved, "success": result}


    def spawn_hermes_agent(self, name: str, reasoning_depth: int = 1, tool_calling_mode: str = "auto") -> dict:
        hermes = hermes_agent.HermesAgent(
            model="gemma3:1b",
            reasoning_depth=reasoning_depth,
            tool_calling_mode=tool_calling_mode,
        )
        session_id = str(uuid.uuid4())[:8]
        agent = {
            "id": session_id,
            "name": name,
            "type": "hermes",
            "reasoning_depth": reasoning_depth,
            "tool_calling_mode": tool_calling_mode,
            "status": "running",
            "created_at": datetime.now().isoformat(),
        }
        agent_file = AGENTS_DIR / f"{session_id}.json"
        agent_file.write_text(json.dumps(agent, indent=2, default=str), encoding="utf-8")
        self.active_sessions[session_id] = agent
        return {"status": "ok", "agent_id": session_id, "agent": agent}

    def execute_mimo_task(self, inputs: list, task_description: str = "") -> dict:
        mimo = multimodal_engine.MimoArchitecture()
        for inp in inputs:
            mimo.add_input(inp.get("name", "input"), inp.get("type", "text"), inp.get("data"), inp.get("priority", 1))
        results = asyncio.run(mimo.process_multi_input(inputs, Task(description=task_description)))
        merged = asyncio.run(mimo.merge_outputs(results))
        return {"status": "ok", "inputs_processed": len(inputs), "merged_output": merged}

    def get_stream_status(self) -> dict:
        return {"status": "ok", "channels": []}

    def set_reasoning_depth(self, depth: int) -> dict:
        return {"status": "ok", "reasoning_depth": depth}

    def route_task(self, task_description: str) -> dict:
        router = moe_router.MoERouter()
        classification = router.classifier.classify(task_description)
        expert = router.policy.select_expert(classification, list(router.experts.values()))
        return {"status": "ok", "classification": classification, "routed_to": expert.expert_name}


agent_command_center = AgentCommandCenter()


def list_agents() -> list[dict]:
    return agent_command_center.list_agents()

def spawn_agent(name: str, instruction: str = "", model: str = "auto") -> dict:
    return agent_command_center.spawn_agent(name, instruction, model)

def update_agent(agent_id: str, status: str, task: str = None) -> dict:
    return agent_command_center.update_agent(agent_id, status, task)