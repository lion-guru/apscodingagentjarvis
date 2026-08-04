"""
Main Orchestrator - Async multi-agent development pipeline.

Coordinates all agents in a continuous loop:
  1. Discover tasks from multiple sources
  2. Assign tasks to appropriate agents
  3. Execute agents concurrently
  4. Verify with E2E tests
  5. Report progress
  6. Repeat

Usage:
  py main.py [--continuous] [--cycles N] [--interval SECONDS]
"""

import asyncio
import json
import os
import sys
import time
import argparse
from typing import List, Dict, Any, Optional

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
_grandparent_dir = os.path.dirname(_parent_dir)

if _grandparent_dir not in sys.path:
    sys.path.insert(0, _grandparent_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from py_agentic.tools.shell import ShellTool
from py_agentic.tools.filesystem import FilesystemTool
from py_agentic.ollama_client import OllamaClient
from py_agentic.task_discovery import TaskDiscovery
from py_agentic.agents.base_agent import BaseAgent, AgentResult
from py_agentic.agents.backend_agent import BackendAgent
from py_agentic.agents.frontend_agent import FrontendAgent
from py_agentic.agents.qa_agent import QAAgent
from py_agentic.agents.security_agent import SecurityAgent
from py_agentic.agents.devops_agent import DevOpsAgent
from py_agentic.agents.architecture_agent import ArchitectureAgent
from py_agentic.agents.documentation_agent import DocumentationAgent
from py_agentic.agents.crm_agent import CRMAgent
from py_agentic.agents.planner_agent import PlannerAgent
from py_agentic.agents.data_analyst_agent import DataAnalystAgent
from py_agentic.agents.uiux_engineer_agent import UIUXEngineerAgent


class Orchestrator:
    """Async orchestrator for multi-agent development."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(_parent_dir, 'config.json')

        with open(config_path) as f:
            self.config = json.load(f)

        self.project_root = self.config['project_root']

        # Use proper Windows-compatible path handling for log/state files
        _base_dir = _parent_dir.replace('/', os.sep)
        self.log_file = os.path.join(_base_dir, 'logs', 'agent_heartbeat.log')
        self.state_file = os.path.join(_base_dir, 'state', 'agent_state.json')

        self.shell = ShellTool(self.project_root)
        self.fs = FilesystemTool(self.project_root)
        self.ollama = OllamaClient(self.config.get('ollama', {}))

        self.discovery = TaskDiscovery(self.project_root, self.shell)

        self.agents: List[BaseAgent] = []
        self._init_agents()

        self.cycle = 0
        self.running = True

    def _init_agents(self):
        """Initialize all 7 specialized agents."""
        agent_configs = {
            'backend': BackendAgent,
            'frontend': FrontendAgent,
            'qa': QAAgent,
            'security': SecurityAgent,
            'devops': DevOpsAgent,
            'architecture': ArchitectureAgent,
            'docs': DocumentationAgent,
            'crm': CRMAgent,
            'planner': PlannerAgent,
            'data_analyst': DataAnalystAgent,
            'uiux': UIUXEngineerAgent,
        }

        for agent_cfg in self.config.get('agents', []):
            agent_id = agent_cfg['id']
            cls = agent_configs.get(agent_id)
            if cls:
                agent = cls(
                    agent_id=agent_id,
                    name=agent_cfg['name'],
                    role=agent_cfg['role'],
                    description=agent_cfg['description'],
                    tools=agent_cfg.get('tools', []),
                    shell=self.shell,
                    fs=self.fs,
                    ollama=self.ollama,
                    config=self.config
                )
                self.agents.append(agent)
                self._log(f"Initialized agent: {agent_cfg['name']} ({agent_id})")

    def _log(self, message: str) -> None:
        """Log to file and console (with error handling)."""
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line)
        except (IOError, OSError) as e:
            # Fallback to console only if file writing fails
            pass
        print(line, end='')

    def _save_state(self, state: dict = None) -> None:
        """Save agent state."""
        if state is None:
            state = {}
        state['last_cycle'] = self.cycle
        state['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
        state['total_cycles'] = state.get('total_cycles', 0) + 1
        state['project'] = self.config['project']
        state['mode'] = self.config['scheduler']['mode']
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (IOError, OSError):
            pass

    def _load_state(self) -> dict:
        """Load agent state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _assign_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Assign tasks to appropriate agents."""
        assignments: Dict[str, List[Dict[str, Any]]] = {a.agent_id: [] for a in self.agents}

        for task in tasks:
            task_type = task.get('type', '')
            assigned = False

            for agent in self.agents:
                if agent.can_handle(task_type):
                    assignments[agent.agent_id].append(task)
                    assigned = True
                    break

            if not assigned:
                assignments['backend'].append(task)

        return assignments

    async def _run_cycle(self) -> List[AgentResult]:
        """Run a single orchestrator cycle."""
        self.cycle += 1
        self._log(f"--- CYCLE {self.cycle} ---")

        # 1. Discover tasks
        tasks = self.discovery.discover()
        if tasks:
            self._log(f"Discovered {len(tasks)} task(s): {', '.join(t['type'] for t in tasks)}")
        else:
            self._log("No new tasks discovered - system idle")

        # 2. Assign tasks to agents
        assignments = self._assign_tasks(tasks)
        for agent_id, agent_tasks in assignments.items():
            if agent_tasks:
                self._log(f"  {agent_id}: {len(agent_tasks)} task(s)")

        # 3. Execute agents concurrently
        all_results: List[AgentResult] = []
        for agent in self.agents:
            agent_tasks = assignments.get(agent.agent_id, [])
            if agent_tasks:
                results = await asyncio.gather(
                    *[agent.process_task(task) for task in agent_tasks],
                    return_exceptions=True
                )
                for r in results:
                    if isinstance(r, Exception):
                        all_results.append(AgentResult(
                            agent_id=agent.agent_id,
                            task_type='unknown',
                            success=False,
                            description='Agent exception',
                            error=str(r)
                        ))
                    else:
                        all_results.append(r)

        # 4. Log results
        for result in all_results:
            status = 'OK' if result.success else 'FAIL'
            self._log(f"  [{result.agent_id}] {result.task_type}: {status} "
                      f"({result.duration_sec:.1f}s) - {len(result.changes_made)} changes")
            if result.error:
                self._log(f"    Error: {result.error}")

        # 5. Save state
        self._save_state()

        return all_results

    async def run(self, max_cycles: int = 999, interval_ms: int = 30000) -> None:
        """Run the orchestrator loop."""
        self._log("=== AUTONOMOUS AGENTIC DEV SYSTEM STARTED (Python) ===")
        self._log(f"Project: {self.config['project']}")
        self._log(f"Agents: {len(self.agents)}")
        self._log(f"Mode: {self.config['scheduler']['mode']}")
        self._log(f"AI Backend: {'Ollama available' if self.ollama.is_available() else 'Ollama not available'}")

        state = self._load_state()
        self.cycle = state.get('last_cycle', 0)

        while self.running and self.cycle < max_cycles:
            try:
                await self._run_cycle()
            except Exception as e:
                self._log(f"ERROR in cycle {self.cycle}: {e}")
                self._save_state()
                await asyncio.sleep(5)

            if self.cycle < max_cycles:
                await asyncio.sleep(interval_ms / 1000.0)

        self._log(f"=== ORCHESTRATOR STOPPED (cycle {self.cycle}/{max_cycles}) ===")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='APS Dream Home Agentic Dev System (Python)')
    parser.add_argument('--continuous', action='store_true', default=True,
                        help='Run continuously (default)')
    parser.add_argument('--cycles', type=int, default=999,
                        help='Max cycles to run (default: 999)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Interval between cycles in seconds (default: 30)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config.json')
    parser.add_argument('--skip-e2e', action='store_true',
                        help='Skip E2E tests (for quick testing)')
    args = parser.parse_args()

    orchestrator = Orchestrator(config_path=args.config)

    if args.skip_e2e:
        orchestrator.config['e2e_tests']['command'] = 'echo E2E tests skipped'

    await orchestrator.run(
        max_cycles=args.cycles,
        interval_ms=args.interval * 1000
    )


if __name__ == '__main__':
    asyncio.run(main())
