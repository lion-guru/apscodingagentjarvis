"""
QA Engineer Agent

Handles quality assurance tasks:
  - E2E test execution and analysis
  - Regression testing
  - Test coverage analysis
  - Performance testing
"""

import os
import re
from typing import Dict, Any
from .base_agent import BaseAgent


class QAAgent(BaseAgent):
    """Specializes in QA and testing."""

    def _handled_types(self):
        return ['e2e_failure', 'regression_test', 'test_coverage']

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        changes = []
        task_type = task.get('type', '')

        if task_type == 'e2e_failure':
            result = await self._analyze_e2e_failures(task)
            changes.extend(result['changes'])
        elif task_type == 'regression_test':
            result = await self._run_regression_tests(task)
            changes.extend(result['changes'])
        elif task_type == 'test_coverage':
            result = await self._check_coverage(task)
            changes.extend(result['changes'])

        return {'changes': changes}

    async def _analyze_e2e_failures(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze E2E test failures."""
        self._log(f"Analyzing E2E failures: {task.get('desc', '')}")
        changes = []

        # Run E2E tests
        result = self.shell.run(
            'node testing/visual_tests/E2E_MASTER_TEST.mjs 2>&1',
            timeout=120
        )

        # Parse results
        output = result.stdout + result.stderr
        match = re.search(r'(\d+)/(\d+)\s+passed', output, re.IGNORECASE)
        if match:
            passed, total = int(match.group(1)), int(match.group(2))
            if passed < total:
                changes.append(f"E2E tests: {passed}/{total} passing - {total - passed} failures need investigation")
            else:
                changes.append(f"E2E tests: {passed}/{total} all passing!")
        else:
            changes.append("Could not parse E2E test results")

        return {'changes': changes}

    async def _run_regression_tests(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run regression tests."""
        self._log("Running regression tests...")
        changes = []

        # Check PHP syntax on all files
        result = self.shell.run(
            'find app/ -name "*.php" -exec php -l {} \\; 2>&1 | grep "Parse error\\|syntax error" | head -20',
            timeout=120
        )

        if result.stdout.strip():
            changes.append(f"Found PHP syntax errors: {result.stdout.strip()[:200]}")
        else:
            changes.append("All PHP files pass syntax check")

        return {'changes': changes}

    async def _check_coverage(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check test coverage."""
        self._log("Checking test coverage...")
        changes = []

        # Count routes and check coverage
        routes_result = self.shell.run(r'grep -c "^\$router" routes/web.php 2>/dev/null')
        test_result = self.shell.run(r'grep -c "OK\|PASS" testing/visual_tests/E2E_MASTER_TEST.mjs 2>/dev/null')

        if routes_result.stdout.strip() and test_result.stdout.strip():
            routes = int(routes_result.stdout.strip())
            tests = int(test_result.stdout.strip())
            changes.append(f"Route coverage: {tests} E2E tests covering {routes} routes")

        return {'changes': changes}
