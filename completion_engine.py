"""
DevMind Completion Engine
Tab completion and Supercomplete-style code predictions.
Provides inline suggestions based on context, AST analysis, and pattern matching.
"""
import os
import re
from pathlib import Path
from datetime import datetime

COMPLETIONS_DIR = Path.home() / ".devmind" / "completions"

class CompletionEngine:
    def __init__(self):
        COMPLETIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.completion_history = []
        self.suggestions_cache = {}

    def get_completions(self, file_path: str, line: str, cursor_pos: int,
                        context: str = "", language: str = "python") -> list[dict]:
        """Get code completions based on current context."""
        suggestions = []

        if language == "python":
            suggestions.extend(self._python_completions(line, cursor_pos, context))
        elif language in ("javascript", "typescript"):
            suggestions.extend(self._js_completions(line, cursor_pos, context))
        elif language == "html":
            suggestions.extend(self._html_completions(line, cursor_pos, context))

        suggestions.extend(self._keyword_completions(line, cursor_pos, language))
        suggestions.extend(self._path_completions(line, cursor_pos))

        seen = set()
        unique = []
        for s in suggestions:
            key = s.get("label", s.get("text", ""))
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique[:50]

    def _python_completions(self, line: str, cursor_pos: int, context: str) -> list[dict]:
        suggestions = []

        builtins = [
            "print(", "len(", "range(", "enumerate(", "zip(", "map(", "filter(",
            "sorted(", "reversed(", "sum(", "max(", "min(", "any(", "all(",
            "isinstance(", "hasattr(", "getattr(", "setattr(", "dir(", "type(",
            "super(", "self.", "cls.", "True", "False", "None", "lambda ",
            "def ", "class ", "import ", "from ", "return ", "yield ",
            "async ", "await ", "try:", "except ", "finally:", "with ",
            "if ", "elif ", "else:", "for ", "while ", "break", "continue",
            "pass", "raise ", "assert ", "global ", "nonlocal ", "del ",
            "and ", "or ", "not ", "in ", "is ", "True", "False", "None",
        ]

        for kw in builtins:
            if kw.startswith(line.strip()[:cursor_pos].split()[-1] if line.strip() else ""):
                suggestions.append({
                    "label": kw.rstrip("("),
                    "type": "keyword",
                    "insertText": kw,
                    "detail": "Python keyword / built-in",
                })

        stdlib_modules = [
            "os", "sys", "json", "re", "pathlib", "datetime", "collections",
            "itertools", "functools", "typing", "dataclasses", "asyncio",
            "subprocess", "threading", "multiprocessing", "hashlib", "hmac",
            "base64", "urllib", "http", "email", "logging", "unittest",
            "math", "random", "decimal", "fractions", "statistics",
        ]
        for mod in stdlib_modules:
            suggestions.append({
                "label": mod,
                "type": "module",
                "insertText": mod,
                "detail": "Python standard library",
            })

        return suggestions

    def _js_completions(self, line: str, cursor_pos: int, context: str) -> list[dict]:
        suggestions = []

        js_builtins = [
            "console.log(", "document.getElementById(", "document.querySelector(",
            "JSON.parse(", "JSON.stringify(", "Array.from(", "Object.keys(",
            "Object.values(", "Promise.resolve(", "fetch(", "addEventListener(",
            "setTimeout(", "setInterval(", "clearTimeout(", "clearInterval(",
            "Math.floor(", "Math.ceil(", "Math.round(", "Math.random(",
            "String(", "Number(", "Boolean(", "Array(", "Object(",
            "const ", "let ", "var ", "function ", "return ", "if ", "else ",
            "for ", "while ", "class ", "import ", "export ", "async ", "await ",
            "try {", "catch ", "finally {", "throw ", "new ", "this.",
            "true", "false", "null", "undefined", "NaN", "Infinity",
        ]

        for kw in js_builtins:
            suggestions.append({
                "label": kw.rstrip("(").rstrip(" {").rstrip(";"),
                "type": "keyword",
                "insertText": kw,
                "detail": "JavaScript built-in",
            })

        return suggestions

    def _html_completions(self, line: str, cursor_pos: int, context: str) -> list[dict]:
        suggestions = []

        html_tags = [
            "<div>", "</div>", "<span>", "</span>", "<p>", "</p>",
            "<a href=\"\">", "<img src=\"\" alt=\"\">", "<ul>", "</ul>",
            "<li>", "</li>", "<h1>", "</h1>", "<h2>", "</h2>",
            "<input type=\"text\">", "<button>", "</button>", "<form>", "</form>",
            "<table>", "</table>", "<tr>", "</tr>", "<td>", "</td>",
            "<style>", "</style>", "<script>", "</script>", "<head>", "</head>",
            "<body>", "</body>", "<html>", "</html>", "<title>", "</title>",
        ]

        for tag in html_tags:
            suggestions.append({
                "label": tag.strip("<>").split()[0].split("=")[0],
                "type": "html-tag",
                "insertText": tag,
                "detail": "HTML element",
            })

        return suggestions

    def _keyword_completions(self, line: str, cursor_pos: int, language: str) -> list[dict]:
        keywords = {
            "python": ["def ", "class ", "import ", "from ", "return ", "yield ",
                       "if ", "elif ", "else:", "for ", "while ", "try:", "except ",
                       "finally:", "with ", "assert ", "raise ", "pass", "break",
                       "continue", "lambda ", "del ", "global ", "nonlocal ", "async ", "await "],
            "javascript": ["function ", "const ", "let ", "var ", "return ", "if ",
                           "else ", "for ", "while ", "class ", "new ", "try {",
                           "catch ", "throw ", "async ", "await ", "import ", "export "],
            "typescript": ["interface ", "type ", "enum ", "namespace ", "implements ",
                           "extends ", "abstract ", "readonly ", "as ", "keyof ", "typeof "],
        }

        suggestions = []
        for kw in keywords.get(language, []):
            suggestions.append({
                "label": kw.strip(),
                "type": "keyword",
                "insertText": kw,
                "detail": f"{language} keyword",
            })
        return suggestions

    def _path_completions(self, line: str, cursor_pos: int) -> list[dict]:
        suggestions = []
        path_match = re.search(r'["\']([^"\']*/?)$', line[:cursor_pos])
        if path_match:
            partial = path_match.group(1)
            base = Path(partial).parent if "/" in partial else Path(".")
            if base.exists():
                for item in base.iterdir():
                    suggestions.append({
                        "label": item.name,
                        "type": "path",
                        "insertText": item.name + ("/" if item.is_dir() else ""),
                        "detail": str(item),
                    })
        return suggestions

    def get_supercomplete(self, file_path: str, context: str) -> list[dict]:
        """Get Supercomplete-style predictions based on recent edits and patterns."""
        suggestions = []

        if file_path in self.suggestions_cache:
            suggestions.extend(self.suggestions_cache[file_path])

        for prev in self.completion_history[-10:]:
            if prev.get("file_path") == file_path:
                suggestions.append({
                    "label": prev.get("label", ""),
                    "type": "history",
                    "insertText": prev.get("insertText", ""),
                    "detail": "Previously used",
                })

        return suggestions[:20]

    def record_completion(self, file_path: str, label: str, insert_text: str):
        """Record a completion for future Supercomplete predictions."""
        self.completion_history.append({
            "file_path": file_path,
            "label": label,
            "insertText": insert_text,
            "timestamp": datetime.now().isoformat(),
        })

        if file_path not in self.suggestions_cache:
            self.suggestions_cache[file_path] = []
        self.suggestions_cache[file_path].append({
            "label": label,
            "type": "history",
            "insertText": insert_text,
            "detail": "Previously used",
        })


completion_engine = CompletionEngine()


def get_completions(file_path: str = "", line: str = "", cursor_pos: int = 0, context: str = "", language: str = "python") -> list:
    return completion_engine.get_completions(file_path, line, cursor_pos, context, language)

def record_completion(file_path: str, label: str = "", insert_text: str = "") -> dict:
    return completion_engine.record_completion(file_path, label, insert_text)