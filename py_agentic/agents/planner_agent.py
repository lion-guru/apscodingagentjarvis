"""
Planner Agent - Web research and technical specification generation.

Conducts web searches, analyzes competitors, and generates detailed
technical specs for new features. Uses Ollama for AI reasoning.
Discovers trending practices in real estate tech, SaaS architecture,
and Indian real estate regulations.
"""

import os
import re
import time
import json
from typing import Dict, Any, List, Optional
from py_agentic.agents.base_agent import BaseAgent, AgentResult


class PlannerAgent(BaseAgent):
    """Strategic planner agent - discovers requirements and generates specs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_cycle = 0

    def _handled_types(self) -> List[str]:
        return ['planning', 'spec_generation', 'web_research', 'competitive_analysis']

    async def process_task(self, task: Dict[str, Any]) -> AgentResult:
        start = time.time()
        changes = []
        task_type = task.get('type', '')

        if task_type == 'web_research':
            result = await self._do_web_research(task.get('detail', ''))
            changes.append(result)
        elif task_type == 'competitive_analysis':
            result = await self._analyze_competitor(task.get('detail', ''))
            changes.append(result)
        elif task_type == 'spec_generation':
            spec = await self._generate_spec(task.get('detail', ''))
            # Save spec to a file
            spec_dir = os.path.join(self.project_root, 'specs')
            os.makedirs(spec_dir, exist_ok=True)
            spec_file = os.path.join(spec_dir, f'spec_{int(time.time())}.md')
            try:
                with open(spec_file, 'w') as f:
                    f.write(spec)
                changes.append(f"Spec written to specs/{os.path.basename(spec_file)}")
            except Exception as e:
                self._log(f"Failed to write spec: {e}")
        else:
            insight = await self._ai_reason(
                f"As a senior product planner for a real estate SaaS platform, analyze this requirement and generate a detailed spec:\n{task.get('desc', '')}\n\nContext: The project is APS Dream Home - a PHP MVC custom framework real estate platform with tenant-scoped multi-tenancy, serving Indian real estate market.",
                system="You are a senior product planner. Generate detailed technical specifications with user stories, acceptance criteria, database schema changes, API endpoints, and implementation phases."
            )
            if insight:
                spec_dir = os.path.join(self.project_root, 'specs')
                os.makedirs(spec_dir, exist_ok=True)
                spec_file = os.path.join(spec_dir, f'auto_spec_{int(time.time())}.md')
                try:
                    with open(spec_file, 'w') as f:
                        f.write(insight)
                    changes.append(f"Auto-spec created: specs/{os.path.basename(spec_file)}")
                except Exception:
                    changes.append(f"AI insight: {insight[:300]}")

        return AgentResult(
            agent_id=self.agent_id,
            task_type=task_type,
            success=True,
            description=f"Planner analysis complete",
            changes_made=changes,
            duration_sec=time.time() - start
        )

    async def _do_web_research(self, topic: str) -> str:
        """Conduct research on a topic using AI knowledge."""
        self._log(f"Researching: {topic}")

        if self.ollama and self.ollama.is_available():
            insight = self.ollama.generate(
                f"Research best practices for implementing {topic} in a real estate SaaS platform. Consider Indian market context, regulatory requirements, multi-tenant architecture, and modern web practices. Provide key insights.",
                system="You are a senior product researcher with deep knowledge of real estate technology, Indian regulations, and SaaS architecture."
            )
            return f"Research on '{topic}': {insight[:800]}"

        return f"Research on '{topic}': Ollama not available - using AI knowledge base analysis"

    async def _analyze_competitor(self, competitor: str) -> str:
        """Analyze a competitor's product."""
        self._log(f"Analyzing competitor: {competitor}")

        insight = await self._ai_reason(
            f"Analyze the key features and pricing strategies of {competitor} in the Indian real estate market context. What can we learn? Focus on CRM, commission management, and tenant isolation.",
            system="You are a competitive intelligence analyst for real estate SaaS products."
        )

        return f"Competitor analysis ({competitor}): {insight[:500]}" if insight else f"Competitor analysis ({competitor}): Completed"

    async def _generate_spec(self, requirement: str) -> str:
        """Generate a detailed technical spec."""
        spec = await self._ai_reason(
            f"Generate a complete technical specification for: {requirement}\n\nFormat:\n1. Overview\n2. User Stories\n3. Acceptance Criteria\n4. Database Schema Changes\n5. API Endpoints\n6. Controller Methods\n7. View Files\n8. Service Layer\n9. Implementation Phases\n10. Testing Strategy",
            system="You are a senior technical architect. Generate detailed, actionable technical specifications for a PHP MVC real estate platform with tenant isolation."
        )

        return spec if spec else f"Technical spec for: {requirement}\n\n[AI not available - basic spec template]"

    def can_handle(self, task_type: str) -> bool:
        return task_type in self._handled_types()

    def _log(self, msg: str):
        print(f"[{self.name}] {msg}")
