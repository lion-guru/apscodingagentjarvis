"""
Documentation Engineer Agent

Handles documentation tasks:
  - AGENTS.md updates
  - Changelog generation
  - Code documentation
  - README maintenance
"""

import os
import re
from typing import Dict, Any
from .base_agent import BaseAgent


class DocumentationAgent(BaseAgent):
    """Specializes in documentation and knowledge management."""

    def _handled_types(self):
        return ['docs_update', 'changelog', 'code_documentation']

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        changes = []
        task_type = task.get('type', '')

        if task_type == 'docs_update':
            result = await self._update_docs(task)
            changes.extend(result['changes'])
        elif task_type == 'changelog':
            result = await self._generate_changelog(task)
            changes.extend(result['changes'])
        elif task_type == 'code_documentation':
            result = await self._improve_code_docs(task)
            changes.extend(result['changes'])

        return {'changes': changes}

    async def _update_docs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update project documentation."""
        self._log("Updating documentation...")
        changes = []

        # Check AGENTS.md for stale entries
        ag_path = os.path.join(self.project_root, 'AGENTS.md')
        if os.path.exists(ag_path):
            with open(ag_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if E2E count is current
            if '153/153' not in content:
                changes.append("AGENTS.md may need E2E test count update")

            # Check for stale dates
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
            if date_match:
                changes.append(f"AGENTS.md last updated: {date_match.group(1)}")

        return {'changes': changes}

    async def _generate_changelog(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate changelog from git history."""
        self._log("Generating changelog...")
        changes = []

        # Get recent git log
        result = self.shell.git_log(10)
        if result:
            changes.append(f"Recent commits (last 10):\n{result[:500]}")

        return {'changes': changes}

    async def _improve_code_docs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Improve code documentation."""
        self._log("Improving code documentation...")
        changes = []

        # Find files without docblocks
        php_files = self.fs.glob('app/Services/**/*.php')
        undocumented = []

        for file_path in php_files[:20]:  # Check first 20
            content = self.fs.read_file(file_path)
            if content and '/**' not in content[:200]:  # No docblock at top
                undocumented.append(file_path)

        if undocumented:
            changes.append(f"Found {len(undocumented)} files without docblocks (showing first 20)")

        return {'changes': changes}
