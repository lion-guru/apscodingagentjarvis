import subprocess
import re
import os
from typing import List, Dict, Optional


class LinterEngine:
    def __init__(self):
        self.linters = {
            "pylint": {"cmd": ["pylint", "--output-format=json"], "enabled": True},
            "flake8": {"cmd": ["flake8", "--format=json"], "enabled": True},
            "mypy": {"cmd": ["mypy", "--show-error-codes", "--json-report", "/tmp/mypy"], "enabled": False},
            "ruff": {"cmd": ["ruff", "check", "--output-format=json"], "enabled": True},
        }
        self.diagnostics = []

    def lint_file(self, filepath: str, linters: Optional[List[str]] = None) -> List[Dict]:
        if linters is None:
            linters = ["ruff", "pylint", "flake8"]
        self.diagnostics = []
        for linter_name in linters:
            if linter_name not in self.linters:
                continue
            linter = self.linters[linter_name]
            if not linter["enabled"]:
                continue
            try:
                result = self._run_linter(linter_name, linter["cmd"], filepath)
                self.diagnostics.extend(result)
            except Exception:
                pass
        return self.diagnostics

    def _run_linter(self, name: str, cmd: List[str], filepath: str) -> List[Dict]:
        full_cmd = cmd + [filepath]
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(os.path.abspath(filepath)) or "."
            )
            output = result.stdout.strip()
            if not output:
                return []
            if name == "ruff":
                return self._parse_ruff(output, filepath)
            elif name == "pylint":
                return self._parse_pylint(output, filepath)
            elif name == "flake8":
                return self._parse_flake8(output, filepath)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []
        return []

    def _parse_ruff(self, output: str, filepath: str) -> List[Dict]:
        diagnostics = []
        try:
            data = eval(output) if output.startswith("[") else []
            if isinstance(data, list):
                for item in data:
                    diagnostics.append({
                        "source": "ruff",
                        "line": item.get("location", {}).get("row", 1),
                        "column": item.get("location", {}).get("column", 1),
                        "message": item.get("message", ""),
                        "code": item.get("code", ""),
                        "severity": self._ruff_severity(item.get("rule", {}).get("level", "warning")),
                        "filepath": filepath
                    })
        except (SyntaxError, ValueError):
            lines = output.split("\n")
            for line in lines:
                match = re.match(r"^(.+?):(\d+):(\d+):\s*(\w+)\s*(.*)$", line)
                if match:
                    diagnostics.append({
                        "source": "ruff",
                        "line": int(match.group(2)),
                        "column": int(match.group(3)),
                        "message": match.group(5),
                        "code": match.group(4),
                        "severity": "warning",
                        "filepath": filepath
                    })
        return diagnostics

    def _parse_pylint(self, output: str, filepath: str) -> List[Dict]:
        diagnostics = []
        try:
            data = eval(output) if output.startswith("[") else []
            if isinstance(data, list):
                for item in data:
                    diagnostics.append({
                        "source": "pylint",
                        "line": item.get("line", 1),
                        "column": item.get("column", 1),
                        "message": item.get("message", ""),
                        "code": item.get("message-id", ""),
                        "severity": self._pylint_severity(item.get("type", "warning")),
                        "filepath": filepath
                    })
        except (SyntaxError, ValueError):
            for line in output.split("\n"):
                match = re.match(r"^(.+?):(\d+),(\d+):\s*\[(\w+)\]\s*(.*)$", line)
                if match:
                    diagnostics.append({
                        "source": "pylint",
                        "line": int(match.group(2)),
                        "column": int(match.group(3)),
                        "message": match.group(5),
                        "code": match.group(4),
                        "severity": self._pylint_severity("warning"),
                        "filepath": filepath
                    })
        return diagnostics

    def _parse_flake8(self, output: str, filepath: str) -> List[Dict]:
        diagnostics = []
        for line in output.split("\n"):
            match = re.match(r"^(.+?):(\d+):(\d+):\s*(\w+)\s*(.*)$", line)
            if match:
                diagnostics.append({
                    "source": "flake8",
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "message": match.group(5),
                    "code": match.group(4),
                    "severity": "warning",
                    "filepath": filepath
                })
        return diagnostics

    def _ruff_severity(self, level: str) -> str:
        mapping = {"error": "error", "warning": "warning", "info": "info", "convention": "info"}
        return mapping.get(level, "warning")

    def _pylint_severity(self, ptype: str) -> str:
        mapping = {"error": "error", "warning": "warning", "refactor": "info", "convention": "info", "fatal": "error"}
        return mapping.get(ptype, "warning")

    def get_diagnostics_summary(self, diagnostics: List[Dict]) -> Dict:
        errors = [d for d in diagnostics if d.get("severity") == "error"]
        warnings = [d for d in diagnostics if d.get("severity") == "warning"]
        infos = [d for d in diagnostics if d.get("severity") == "info"]
        return {
            "total": len(diagnostics),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(infos),
            "diagnostics": diagnostics
        }

    def get_auto_fix(self, filepath: str, diagnostics: List[Dict]) -> List[Dict]:
        fixes = []
        for diag in diagnostics:
            if diag.get("source") == "ruff" and diag.get("code") in ["E501", "F401", "F841", "F811"]:
                fixes.append({
                    "line": diag["line"],
                    "message": diag["message"],
                    "suggestion": self._get_fix_suggestion(diag)
                })
        return fixes

    def _get_fix_suggestion(self, diag: Dict) -> str:
        code = diag.get("code", "")
        if code == "E501":
            return "Line too long. Consider breaking into multiple lines."
        elif code == "F401":
            return "Unused import. Remove the import statement."
        elif code == "F841":
            return "Unused variable. Remove or use the variable."
        elif code == "F811":
            return "Redefined name. Rename the variable or function."
        return diag.get("message", "")


linter_engine = LinterEngine()


def lint_file(filepath: str, linters: Optional[List[str]] = None) -> List[Dict]:
    return linter_engine.lint_file(filepath, linters)

def get_diagnostics_summary(diagnostics: List[Dict]) -> Dict:
    return linter_engine.get_diagnostics_summary(diagnostics)

def get_auto_fix(filepath: str, diagnostics: List[Dict]) -> List[Dict]:
    return linter_engine.get_auto_fix(filepath, diagnostics)