"""
Filesystem Tool - File operations for agents.

Provides read, write, grep, glob, and other filesystem operations
that agents need to inspect and modify the codebase.
"""

import os
import re
import glob as glob_module
from typing import List, Tuple, Optional


class FilesystemTool:
    """Filesystem operations for agents."""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def _resolve(self, path: str) -> str:
        """Resolve a path relative to project root."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.project_root, path)

    def read_file(self, path: str) -> str:
        """Read a file and return its contents."""
        full_path = self._resolve(path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ''

    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        full_path = self._resolve(path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def append_file(self, path: str, content: str) -> bool:
        """Append content to a file."""
        full_path = self._resolve(path)
        try:
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        return os.path.exists(self._resolve(path))

    def grep(self, pattern: str, path: str = '', include: str = '*',
             exclude: str = '', max_results: int = 100) -> List[Tuple[str, int, str]]:
        """
        Search for a pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search (relative to project root)
            include: File pattern to include (e.g., '*.php')
            exclude: File pattern to exclude
            max_results: Maximum number of results

        Returns:
            List of (file_path, line_number, line_content) tuples
        """
        search_path = self._resolve(path) if path else self.project_root
        results = []

        include_patterns = include.split(',') if include else ['*']
        exclude_patterns = exclude.split(',') if exclude else []

        regex = re.compile(pattern, re.IGNORECASE)

        for root, dirs, files in os.walk(search_path):
            # Skip _archive and vendor directories
            dirs[:] = [d for d in dirs if d not in ('_archive', 'vendor', 'node_modules', '.git')]

            for filename in files:
                # Check include patterns
                if not any(glob_module.fnmatch.fnmatch(filename, p) for p in include_patterns):
                    continue

                # Check exclude patterns
                if any(glob_module.fnmatch.fnmatch(filename, p) for p in exclude_patterns):
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = os.path.relpath(filepath, self.project_root)
                                results.append((rel_path, line_num, line.rstrip()))
                                if len(results) >= max_results:
                                    return results
                except Exception:
                    continue

        return results

    def glob(self, pattern: str, path: str = '') -> List[str]:
        """Find files matching a glob pattern."""
        search_path = self._resolve(path) if path else self.project_root
        full_pattern = os.path.join(search_path, pattern)
        matches = glob_module.glob(full_pattern, recursive=True)
        return [os.path.relpath(m, self.project_root) for m in matches]

    def list_dir(self, path: str = '') -> List[str]:
        """List contents of a directory."""
        full_path = self._resolve(path)
        try:
            return os.listdir(full_path)
        except Exception:
            return []

    def read_lines(self, path: str, start: int = 0, count: int = 50) -> List[str]:
        """Read specific lines from a file."""
        content = self.read_file(path)
        if not content:
            return []
        lines = content.split('\n')
        return lines[start:start + count]
