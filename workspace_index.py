"""
DevMind Workspace Index
AST symbols + import graph + cross-file references.
Provides workspace-level code intelligence.
"""
import json
import ast
import re
from pathlib import Path
from collections import defaultdict

INDEX_FILE = Path.home() / ".devmind" / "workspace_index.json"

class WorkspaceIndex:
    def __init__(self):
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not INDEX_FILE.exists():
            INDEX_FILE.write_text(json.dumps({"symbols": [], "imports": {}, "references": {}, "files": []}, indent=2), encoding="utf-8")

    def index_workspace(self, workspace_path: str = "E:\\coding-assistant") -> dict:
        """Build workspace index with AST symbols and import graph."""
        try:
            target_dir = Path(workspace_path)
            if not target_dir.exists():
                return {"status": "error", "error": f"Path not found: {workspace_path}"}

            symbols = []
            imports = {}
            references = {}
            files = []

            for p in target_dir.rglob("*.py"):
                if any(part.startswith(".") or part in ("node_modules", "venv", "__pycache__") for part in p.parts):
                    continue

                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(content)
                    file_symbols = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            file_symbols.append({
                                "name": node.name,
                                "type": "function",
                                "line": node.lineno,
                                "file": str(p),
                            })
                        elif isinstance(node, ast.ClassDef):
                            file_symbols.append({
                                "name": node.name,
                                "type": "class",
                                "line": node.lineno,
                                "file": str(p),
                            })
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.setdefault(str(p), []).append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module or ""
                            for alias in node.names:
                                imports.setdefault(str(p), []).append(f"{module}.{alias.name}")

                    for sym in file_symbols:
                        references.setdefault(sym["name"], []).append(sym)

                    symbols.extend(file_symbols)
                    files.append(str(p))
                except Exception:
                    pass

            index = {
                "symbols": symbols,
                "imports": imports,
                "references": {k: v for k, v in references.items()},
                "files": files,
                "indexed_at": __import__("datetime").datetime.now().isoformat(),
            }

            INDEX_FILE.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")
            return {"status": "ok", "symbols_count": len(symbols), "files_indexed": len(files)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_symbols(self) -> list[dict]:
        """Get all indexed symbols."""
        if not INDEX_FILE.exists():
            return []
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return data.get("symbols", [])

    def find_symbol(self, name: str) -> list[dict]:
        """Find a symbol by name across the workspace."""
        if not INDEX_FILE.exists():
            return []
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return [s for s in data.get("symbols", []) if s.get("name") == name]

    def get_import_graph(self) -> dict:
        """Get the import graph for the workspace."""
        if not INDEX_FILE.exists():
            return {}
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return data.get("imports", {})

    def get_cross_references(self, symbol_name: str) -> list[dict]:
        """Get all references to a symbol across the workspace."""
        if not INDEX_FILE.exists():
            return []
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return data.get("references", {}).get(symbol_name, [])


workspace_index = WorkspaceIndex()


def index_workspace(workspace_path: str = "E:\\coding-assistant") -> dict:
    return workspace_index.index_workspace(workspace_path)

def get_symbols() -> list:
    return workspace_index.get_symbols()

def find_symbol(name: str) -> list:
    return workspace_index.find_symbol(name)

def get_import_graph() -> dict:
    return workspace_index.get_import_graph()

def get_cross_references(symbol_name: str) -> list:
    return workspace_index.get_cross_references(symbol_name)