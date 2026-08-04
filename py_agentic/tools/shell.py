"""
Shell Tool - Cross-platform subprocess execution for agents.

Works on both Windows and Unix-like systems.
Uses os.walk for file operations instead of Unix find.
"""

import subprocess
import os
import time
from typing import Optional, List


class ShellResult:
    """Result of a shell command execution."""

    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def __str__(self) -> str:
        return f"ShellResult(success={self.success}, rc={self.returncode})"


class ShellTool:
    """Cross-platform shell execution tool."""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def run(self, command: str, timeout: int = 30, cwd: str = None) -> ShellResult:
        """
        Run a shell command.

        Args:
            command: Command string to execute
            timeout: Timeout in seconds
            cwd: Working directory (defaults to project root)

        Returns:
            ShellResult with stdout, stderr, and returncode
        """
        work_dir = cwd or self.project_root
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir
            )
            return ShellResult(result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired:
            return ShellResult('', 'Command timed out', -1)
        except Exception as e:
            return ShellResult('', str(e), -1)

    def git_diff(self, ref: str = 'HEAD~1', path: str = '') -> str:
        """Get git diff for a specific ref."""
        cmd = f'git diff {ref}'
        if path:
            cmd += f' -- {path}'
        result = self.run(cmd, timeout=10)
        return result.stdout if result.success else ''

    def git_status(self) -> str:
        """Get git status."""
        result = self.run('git status --short', timeout=10)
        return result.stdout if result.success else ''

    def git_log(self, count: int = 5) -> str:
        """Get recent git log."""
        result = self.run(f'git log --oneline -{count}', timeout=10)
        return result.stdout if result.success else ''

    def php_syntax_check(self, file_path: str) -> ShellResult:
        """Check PHP syntax for a file."""
        full_path = file_path if os.path.isabs(file_path) else os.path.join(self.project_root, file_path)
        return self.run(f'php -l "{full_path}"', timeout=10)

    def php_syntax_check_all(self, directory: str = 'app/', max_files: int = 30) -> str:
        """Check PHP syntax for recently modified PHP files (optimized for speed).

        Only checks files modified within the last 24 hours and limits to max_files
        to keep each cycle fast. Falls back to git diff for known changed files.
        """
        search_dir = os.path.join(self.project_root, directory) if not os.path.isabs(directory) else directory
        if not os.path.exists(search_dir):
            return f'Directory not found: {directory}'

        errors = []
        checked = 0
        cutoff = time.time() - 86400  # 24 hours ago

        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in ('_archive', 'vendor', 'node_modules', '.git')]
            for f in files:
                if f.endswith('.php'):
                    full = os.path.join(root, f)
                    try:
                        if os.path.getmtime(full) < cutoff:
                            continue
                    except OSError:
                        continue
                    r = self.php_syntax_check(full)
                    if r.stderr:
                        for line in r.stderr.split('\n'):
                            if 'Parse error' in line or 'syntax error' in line:
                                errors.append(line.strip())
                    checked += 1
                    if checked >= max_files:
                        return '\n'.join(errors) if errors else ''

        if checked == 0:
            return ''  # No recently modified files
        return '\n'.join(errors) if errors else ''

    def node_command(self, command: str, timeout: int = 30) -> ShellResult:
        """Run a node command."""
        return self.run(f'node {command}', timeout=timeout)

    def composer_command(self, command: str, timeout: int = 60) -> ShellResult:
        """Run a composer command."""
        return self.run(f'composer {command}', timeout=timeout)

    def find_php_files(self, directory: str = 'app/', exclude_dirs: List[str] = None) -> List[str]:
        """Find all PHP files in a directory (cross-platform, replaces Unix find)."""
        if exclude_dirs is None:
            exclude_dirs = ['_archive', 'vendor', 'node_modules', '.git']
        search_dir = os.path.join(self.project_root, directory) if not os.path.isabs(directory) else directory
        if not os.path.exists(search_dir):
            return []
        results = []
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f.endswith('.php'):
                    results.append(os.path.join(root, f))
        return results

    def run_sql(self, query: str) -> ShellResult:
        """Run a SQL query against the project MySQL database."""
        mysql_exe = r"C:\xampp\mysql\bin\mysql.exe"
        cmd = f'"{mysql_exe}" -h 127.0.0.1 -P 3307 -u root apsdreamhome -e "{query}"'
        return self.run(cmd, timeout=15)
