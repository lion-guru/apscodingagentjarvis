"""
DevOps Engineer Agent

Handles DevOps tasks:
  - Build automation
  - APK building and deployment
  - Cron job monitoring
  - Infrastructure checks
  - Deployment verification
"""

import os
from typing import Dict, Any
from .base_agent import BaseAgent


class DevOpsAgent(BaseAgent):
    """Specializes in DevOps and deployment."""

    def _handled_types(self):
        return ['archive_growth', 'build_status', 'deployment_check', 'cron_monitor']

    async def _handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        changes = []
        task_type = task.get('type', '')

        if task_type == 'archive_growth':
            result = await self._audit_archive(task)
            changes.extend(result['changes'])
        elif task_type == 'build_status':
            result = await self._check_build_status(task)
            changes.extend(result['changes'])
        elif task_type == 'deployment_check':
            result = await self._check_deployment(task)
            changes.extend(result['changes'])
        elif task_type == 'cron_monitor':
            result = await self._monitor_cron(task)
            changes.extend(result['changes'])

        return {'changes': changes}

    async def _audit_archive(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Audit archive directory for stale files."""
        self._log(f"Auditing archive: {task.get('desc', '')}")
        changes = []

        archive_path = os.path.join(self.project_root, '_archive')
        if not os.path.exists(archive_path):
            return {'changes': changes}

        # Count files and check for stale entries
        file_count = 0
        stale_dirs = []
        for root, dirs, files in os.walk(archive_path):
            file_count += len(files)
            if len(files) == 0 and len(dirs) == 0:
                stale_dirs.append(os.path.relpath(root, archive_path))

        changes.append(f"Archive audit: {file_count} files total")
        if stale_dirs:
            changes.append(f"Found {len(stale_dirs)} empty directories in archive")

        # Check for files older than 6 months (stale candidates)
        import time
        current_time = time.time()
        stale_files = []
        for root, dirs, files in os.walk(archive_path):
            for f in files:
                filepath = os.path.join(root, f)
                mtime = os.path.getmtime(filepath)
                if current_time - mtime > 180 * 24 * 3600:  # 180 days
                    stale_files.append(os.path.relpath(filepath, archive_path))

        if stale_files:
            changes.append(f"Found {len(stale_files)} files older than 6 months - consider permanent deletion")

        return {'changes': changes}

    async def _check_build_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check Flutter build status."""
        self._log("Checking build status...")
        changes = []

        # Check if APK exists
        apk_path = os.path.join(self.project_root, 'public', 'downloads', 'apsdreamhome.apk')
        if os.path.exists(apk_path):
            size_mb = os.path.getsize(apk_path) / (1024 * 1024)
            changes.append(f"APK exists: {size_mb:.1f}MB at public/downloads/apsdreamhome.apk")
        else:
            changes.append("WARNING: APK not found at public/downloads/apsdreamhome.apk")

        return {'changes': changes}

    async def _check_deployment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check deployment readiness."""
        self._log("Checking deployment readiness...")
        changes = []

        # Check for uncommitted changes
        result = self.shell.git_status()
        if result.strip():
            changes.append(f"Uncommitted changes detected - {len(result.strip().split(chr(10)))} file(s)")

        return {'changes': changes}

    async def _monitor_cron(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor cron job execution."""
        self._log("Monitoring cron jobs...")
        changes = []

        cron_log = os.path.join(self.project_root, 'agentic_dev_system', 'logs', 'scheduler.log')
        if os.path.exists(cron_log):
            with open(cron_log, 'r') as f:
                lines = f.readlines()
            if lines:
                last_run = lines[-1].strip() if lines else "No runs"
                changes.append(f"Last cron run: {last_run[-100:]}")

        return {'changes': changes}
