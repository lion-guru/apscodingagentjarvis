import ast
import os
from typing import List, Dict, Optional


class ASTAnalyzer:
    def __init__(self):
        self.symbols = []
        self.imports = []
        self.classes = []
        self.functions = []
        self.errors = []

    def analyze_file(self, filepath: str) -> Dict:
        if not os.path.exists(filepath):
            return {"error": "File not found", "symbols": [], "imports": [], "classes": [], "functions": []}
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            self.symbols = []
            self.imports = []
            self.classes = []
            self.functions = []
            self.errors = []
            self._walk(tree, source)
            return {
                "status": "ok",
                "symbols": self.symbols,
                "imports": self.imports,
                "classes": self.classes,
                "functions": self.functions,
                "errors": self.errors,
                "line_count": source.count("\n") + 1
            }
        except SyntaxError as e:
            return {"error": str(e), "symbols": [], "imports": [], "classes": [], "functions": []}

    def _walk(self, node, source):
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    self.imports.append({"name": alias.name, "alias": alias.asname, "line": child.lineno})
            elif isinstance(child, ast.ImportFrom):
                module = child.module or ""
                for alias in child.names:
                    self.imports.append({"name": f"{module}.{alias.name}", "alias": alias.asname, "line": child.lineno})
            elif isinstance(child, ast.ClassDef):
                self.classes.append({"name": child.name, "line": child.lineno, "bases": [self._get_name(b) for b in child.bases]})
            elif isinstance(child, ast.FunctionDef):
                self.functions.append({"name": child.name, "line": child.lineno, "args": [a.arg for a in child.args.args], "returns": self._get_name(child.returns) if child.returns else None})
            elif isinstance(child, ast.AsyncFunctionDef):
                self.functions.append({"name": child.name, "line": child.lineno, "args": [a.arg for a in child.args.args], "async": True})
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                if not any(s["name"] == child.id for s in self.symbols):
                    self.symbols.append({"name": child.id, "line": child.lineno, "type": "variable"})

    def _get_name(self, node):
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._get_name(node.func)
        return None

    def get_definition(self, filepath: str, symbol_name: str) -> Optional[Dict]:
        result = self.analyze_file(filepath)
        if "error" in result:
            return None
        for func in result.get("functions", []):
            if func["name"] == symbol_name:
                return {"type": "function", **func}
        for cls in result.get("classes", []):
            if cls["name"] == symbol_name:
                return {"type": "class", **cls}
        return None

    def find_references(self, filepath: str, symbol_name: str) -> List[Dict]:
        result = self.analyze_file(filepath)
        if "error" in result:
            return []
        refs = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if symbol_name in line and not line.strip().startswith("#"):
                refs.append({"line": i, "content": line.strip()})
        return refs

    def get_outline(self, filepath: str) -> List[Dict]:
        result = self.analyze_file(filepath)
        if "error" in result:
            return []
        outline = []
        for imp in result.get("imports", []):
            outline.append({"type": "import", "name": imp["name"], "line": imp["line"]})
        for cls in result.get("classes", []):
            outline.append({"type": "class", "name": cls["name"], "line": cls["line"]})
        for func in result.get("functions", []):
            outline.append({"type": "function", "name": func["name"], "line": func["line"]})
        return outline

    def get_import_graph(self, filepath: str) -> Dict:
        result = self.analyze_file(filepath)
        if "error" in result:
            return {"imports": [], "imported_by": []}
        return {"imports": result.get("imports", []), "imported_by": []}


# Module-level instance & wrapper functions
_analyzer = ASTAnalyzer()

def analyze_file(filepath: str) -> Dict:
    return _analyzer.analyze_file(filepath)

def get_definition(filepath: str, symbol_name: str) -> Optional[Dict]:
    return _analyzer.get_definition(filepath, symbol_name)

def find_references(filepath: str, symbol_name: str) -> List[Dict]:
    return _analyzer.find_references(filepath, symbol_name)

def get_outline(filepath: str) -> List[Dict]:
    return _analyzer.get_outline(filepath)

def get_import_graph(filepath: str) -> Dict:
    return _analyzer.get_import_graph(filepath)