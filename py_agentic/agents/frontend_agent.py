"""
Frontend Engineer Agent

Handles Flutter/Dart frontend development tasks:
  - UI/UX improvements
  - Mobile responsiveness fixes
  - Theme and styling consistency
  - Widget architecture improvements
"""

from typing import Dict, Any
from .base_agent import BaseAgent


class FrontendAgent(BaseAgent):
    """Specializes in Flutter frontend development."""

    def _handled_types(self):
        return ['frontend_fix', 'ui_improvement', 'mobile_responsive']

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        changes = []
        task_type = task.get('type', '')

        if task_type == 'frontend_fix':
            result = await self._fix_frontend_issues(task)
            changes.extend(result['changes'])
        elif task_type == 'ui_improvement':
            result = await self._improve_ui(task)
            changes.extend(result['changes'])
        elif task_type == 'mobile_responsive':
            result = await self._fix_responsiveness(task)
            changes.extend(result['changes'])

        return {'changes': changes}

    async def _fix_frontend_issues(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fix frontend issues in Flutter code."""
        self._log("Reviewing Flutter frontend issues...")
        changes = []

        # Check for common Flutter issues
        results = self.fs.grep(
            r'TODO|FIXME|HACK|XXX',
            path='mobile/apsdreamhome_app_v2/lib/',
            include='*.dart'
        )

        for file_path, line_num, line_content in results[:20]:
            changes.append(f"Found TODO in {file_path}:{line_num}: {line_content.strip()[:80]}")

        return {'changes': changes}

    async def _improve_ui(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Improve UI/UX in Flutter code."""
        self._log("Improving UI/UX...")
        changes = []

        # Check for hardcoded colors (should use theme variables)
        results = self.fs.grep(
            r'Color\(0x[0-9A-Fa-f]{8}\)',
            path='mobile/apsdreamhome_app_v2/lib/',
            include='*.dart',
            max_results=50
        )

        if results:
            changes.append(f"Found {len(results)} hardcoded color values - review for theme consistency")

        return {'changes': changes}

    async def _fix_responsiveness(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fix mobile/tablet responsiveness issues."""
        self._log("Checking mobile responsiveness...")
        changes = []

        # Check for touch target sizes
        results = self.fs.grep(
            r'width:\s*\d+\.0,\s*height:\s*\d+\.0',
            path='mobile/apsdreamhome_app_v2/lib/',
            include='*.dart',
            max_results=30
        )

        small_targets = [r for r in results if int(r[2].split('width:')[1].split(',')[0].strip().rstrip('.0')) < 44]
        if small_targets:
            changes.append(f"Found {len(small_targets)} touch targets smaller than 44px")

        return {'changes': changes}
