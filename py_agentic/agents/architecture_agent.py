"""
Architecture Analyst Agent

Handles architecture and code quality tasks:
  - Codebase analysis
  - Dead code detection
  - Dependency analysis
  - Architecture compliance
"""

import os
from typing import Dict, Any
from .base_agent import BaseAgent


class ArchitectureAgent(BaseAgent):
    """Specializes in codebase architecture analysis."""

    def _handled_types(self):
        return ['architecture_review', 'dead_code', 'dependency_check']

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        changes = []
        task_type = task.get('type', '')

        if task_type == 'architecture_review':
            result = await self._review_architecture(task)
            changes.extend(result['changes'])
        elif task_type == 'dead_code':
            result = await self._find_dead_code(task)
            changes.extend(result['changes'])
        elif task_type == 'dependency_check':
            result = await self._check_dependencies(task)
            changes.extend(result['changes'])

        return {'changes': changes}

    async def _review_architecture(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Review overall architecture compliance."""
        self._log("Reviewing architecture...")
        changes = []

        # Count controllers, models, views, services
        controller_count = len(self.fs.glob('app/Http/Controllers/**/*.php'))
        model_count = len(self.fs.glob('app/Models/**/*.php'))
        view_count = len(self.fs.glob('app/views/**/*.php'))
        service_count = len(self.fs.glob('app/Services/**/*.php'))

        changes.append(f"Architecture overview: {controller_count} controllers, {model_count} models, {view_count} views, {service_count} services")

        return {'changes': changes}

    async def _find_dead_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Find dead code in the codebase."""
        self._log("Finding dead code...")
        changes = []

        # Check for unused services
        results = self.fs.grep(
            r'use\s+App\\Services\\',
            path='app/',
            include='*.php',
            max_results=100
        )

        imported_services = set()
        for file_path, line_num, line_content in results:
            match = re.search(r'use\s+(App\\Services\\[a-zA-Z_]+)', line_content)
            if match:
                imported_services.add(match.group(1))

        # Check which services actually exist
        all_services = self.fs.glob('app/Services/**/*.php')
        changes.append(f"Found {len(imported_services)} imported services across {len(all_services)} service files")

        return {'changes': changes}

    async def _check_dependencies(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check for dependency issues."""
        self._log("Checking dependencies...")
        changes = []

        # Check for missing dependencies
        results = self.fs.grep(
            r'require_once|include_once|require|include',
            path='app/',
            include='*.php',
            max_results=50
        )

        broken_includes = []
        for file_path, line_num, line_content in results:
            match = re.search(r'(?:require_once|include_once|require|include)\s*\(?\s*["\']([^"\']+)["\']', line_content)
            if match:
                inc_path = match.group(1)
                if not inc_path.startswith('vendor') and not os.path.exists(os.path.join(self.project_root, inc_path)):
                    broken_includes.append(f"{file_path}:{line_num} - {inc_path}")

        if broken_includes:
            changes.append(f"Found {len(broken_includes)} potentially broken includes")
        else:
            changes.append("All includes appear valid")

        return {'changes': changes}
