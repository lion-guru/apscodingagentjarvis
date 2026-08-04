"""
DevMind Project Explorer
File tree with type icons, symbol tree, and breadcrumb navigation.
Provides file explorer functionality for the IDE sidebar.
"""
import os
import json
from pathlib import Path
from datetime import datetime

FILE_ICONS = {
    ".py": "🐍", ".js": "📜", ".ts": "📘", ".tsx": "⚛️", ".jsx": "⚛️",
    ".html": "🌐", ".css": "🎨", ".scss": "🎨", ".less": "🎨",
    ".json": "📋", ".yaml": "📋", ".yml": "📋", ".toml": "📋",
    ".md": "📝", ".txt": "📄", ".rst": "📄",
    ".png": "🖼️", ".jpg": "🖼️", ".jpeg": "🖼️", ".gif": "🖼️", ".svg": "🖼️",
    ".sql": "🗄️", ".sh": "💻", ".bat": "💻", ".ps1": "💻",
    ".cpp": "⚙️", ".c": "⚙️", ".h": "⚙️", ".hpp": "⚙️",
    ".java": "☕", ".go": "🔵", ".rs": "🦀", ".rb": "💎",
    ".php": "🐘", ".swift": "🦅", ".kt": "🟢", ".scala": "🔴",
    ".dockerfile": "🐳", ".gitignore": "🔒", ".git": "📦",
    ".env": "🔑", ".config": "⚙️", ".ini": "⚙️",
    ".xml": "📄", ".yaml": "📋",
}

FOLDER_ICON = "📁"
DEFAULT_ICON = "📄"

class ProjectExplorer:
    def __init__(self, workspace_path: str = "E:\\coding-assistant"):
        self.workspace = Path(workspace_path)
        self.expanded_dirs = set()
        self.selected_file = None

    def get_file_tree(self, path: str = None, max_depth: int = 5) -> list[dict]:
        """Get file tree structure for the sidebar."""
        if path is None:
            path = str(self.workspace)

        target = Path(path)
        if not target.exists():
            return []

        if target.is_file():
            return [self._file_node(target, 0)]

        return self._build_tree(target, 0, max_depth)

    def _build_tree(self, dir_path: Path, depth: int, max_depth: int) -> list[dict]:
        if depth >= max_depth:
            return []

        entries = []
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return []

        for item in items:
            name = item.name
            if any(part.startswith(".") for part in item.parts[-3:]):
                continue
            if name in ("node_modules", "venv", "__pycache__", ".git", ".devmind"):
                continue

            node = self._file_node(item, depth)
            if item.is_dir():
                node["children"] = self._build_tree(item, depth + 1, max_depth)
                node["expanded"] = str(item) in self.expanded_dirs
            entries.append(node)

        return entries

    def _file_node(self, path: Path, depth: int) -> dict:
        is_dir = path.is_dir()
        ext = path.suffix.lower() if not is_dir else ""
        icon = FILE_ICONS.get(ext, FOLDER_ICON if is_dir else DEFAULT_ICON)

        return {
            "name": path.name,
            "path": str(path),
            "is_dir": is_dir,
            "extension": ext,
            "icon": icon,
            "depth": depth,
            "size": path.stat().st_size if path.is_file() else None,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
        }

    def get_symbols(self, file_path: str) -> list[dict]:
        """Get symbols (functions, classes, variables) from a Python file."""
        try:
            p = Path(file_path)
            if not p.exists() or p.suffix != ".py":
                return []

            content = p.read_text(encoding="utf-8", errors="ignore")
            return self._extract_symbols(content, str(p))
        except Exception:
            return []

    def _extract_symbols(self, content: str, file_path: str) -> list[dict]:
        symbols = []
        try:
            tree = __import__("ast").parse(content)
        except SyntaxError:
            return symbols

        for node in __import__("ast").walk(tree):
            if isinstance(node, __import__("ast").FunctionDef):
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "line": node.lineno,
                    "column": node.col_offset,
                    "file_path": file_path,
                    "icon": "🔧",
                })
            elif isinstance(node, __import__("ast").ClassDef):
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "line": node.lineno,
                    "column": node.col_offset,
                    "file_path": file_path,
                    "icon": "🏗️",
                })
            elif isinstance(node, __import__("ast").Assign):
                for target in node.targets:
                    if isinstance(target, __import__("ast").Name):
                        symbols.append({
                            "name": target.id,
                            "type": "variable",
                            "line": node.lineno,
                            "column": node.col_offset,
                            "file_path": file_path,
                            "icon": "📌",
                        })

        symbols.sort(key=lambda s: (s["line"], s["column"]))
        return symbols

    def get_breadcrumbs(self, file_path: str) -> list[dict]:
        """Get breadcrumb navigation for a file path."""
        path = Path(file_path)
        breadcrumbs = []
        current = path
        while current != current.parent:
            breadcrumbs.append({
                "name": current.name if current != path else current.name,
                "path": str(current),
                "is_file": current == path,
            })
            current = current.parent
        breadcrumbs.reverse()
        return breadcrumbs

    def search_files(self, query: str, max_results: int = 20) -> list[dict]:
        """Search for files by name in the workspace."""
        results = []
        query_lower = query.lower()

        try:
            for p in self.workspace.rglob("*"):
                if p.is_file():
                    if any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__") for part in p.parts):
                        continue
                    if query_lower in p.name.lower():
                        results.append({
                            "name": p.name,
                            "path": str(p),
                            "icon": FILE_ICONS.get(p.suffix.lower(), DEFAULT_ICON),
                            "size": p.stat().st_size,
                        })
                    if len(results) >= max_results:
                        break
        except Exception:
            pass

        return results

    def get_file_content(self, file_path: str, max_lines: int = 5000) -> dict:
        """Get file content with line numbers."""
        try:
            p = Path(file_path)
            if not p.exists():
                return {"status": "error", "error": "File not found"}

            lines = p.read_text(encoding="utf-8", errors="ignore").split('\n')
            return {
                "status": "ok",
                "file_path": file_path,
                "total_lines": len(lines),
                "lines": lines[:max_lines],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


project_explorer = ProjectExplorer()


def get_file_tree(path=None):
    return project_explorer.get_file_tree(path)


def get_symbols(file_path=""):
    return project_explorer.get_symbols(file_path)


def get_breadcrumbs(file_path=""):
    return project_explorer.get_breadcrumbs(file_path)


def search_files(q=""):
    return project_explorer.search_files(q)


def get_file_content(file_path="", max_lines=200):
    return project_explorer.get_file_content(file_path, max_lines)