"""
DevMind Diagnostics Panel
Linting diagnostics, error highlighting, and code quality indicators.
Provides real-time diagnostics for the IDE editor.
"""
import json
from pathlib import Path
from datetime import datetime

DIAGNOSTICS_DIR = Path.home() / ".devmind" / "diagnostics"

class DiagnosticsPanel:
    def __init__(self):
        DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
        self.active_diagnostics = {}

    def run_linting(self, file_path: str) -> dict:
        """Run linter on a file and return diagnostics."""
        try:
            from linter_engine import DevMindLinter
            linter = DevMindLinter()
            result = linter.lint_file(file_path)

            diagnostics = {
                "file_path": file_path,
                "timestamp": datetime.now().isoformat(),
                "error_count": len([d for d in result.get("errors", []) if d.get("severity") == "error"]),
                "warning_count": len([d for d in result.get("errors", []) if d.get("severity") == "warning"]),
                "info_count": len([d for d in result.get("errors", []) if d.get("severity") == "info"]),
                "errors": result.get("errors", []),
            }

            self.active_diagnostics[file_path] = diagnostics
            self._save_diagnostics(file_path, diagnostics)
            return diagnostics
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_diagnostics(self, file_path: str) -> dict:
        """Get diagnostics for a file."""
        if file_path in self.active_diagnostics:
            return self.active_diagnostics[file_path]

        diag_file = DIAGNOSTICS_DIR / f"{Path(file_path).stem}.json"
        if diag_file.exists():
            return json.loads(diag_file.read_text(encoding="utf-8"))

        return {"file_path": file_path, "errors": [], "error_count": 0, "warning_count": 0}

    def clear_diagnostics(self, file_path: str = None) -> dict:
        """Clear diagnostics for a file or all files."""
        if file_path:
            if file_path in self.active_diagnostics:
                del self.active_diagnostics[file_path]
            diag_file = DIAGNOSTICS_DIR / f"{Path(file_path).stem}.json"
            if diag_file.exists():
                diag_file.unlink()
            return {"status": "ok", "message": f"Diagnostics cleared for {file_path}"}
        else:
            self.active_diagnostics.clear()
            if DIAGNOSTICS_DIR.exists():
                for f in DIAGNOSTICS_DIR.glob("*.json"):
                    f.unlink()
            return {"status": "ok", "message": "All diagnostics cleared"}

    def get_diagnostics_summary(self) -> dict:
        """Get a summary of all active diagnostics."""
        total_errors = 0
        total_warnings = 0
        total_info = 0
        files_with_issues = 0

        for file_path, diag in self.active_diagnostics.items():
            total_errors += diag.get("error_count", 0)
            total_warnings += diag.get("warning_count", 0)
            total_info += diag.get("info_count", 0)
            if diag.get("error_count", 0) > 0 or diag.get("warning_count", 0) > 0:
                files_with_issues += 1

        return {
            "total_files_analyzed": len(self.active_diagnostics),
            "files_with_issues": files_with_issues,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_info": total_info,
        }

    def _save_diagnostics(self, file_path: str, diagnostics: dict):
        """Save diagnostics to disk."""
        diag_file = DIAGNOSTICS_DIR / f"{Path(file_path).stem}.json"
        diag_file.write_text(json.dumps(diagnostics, indent=2, default=str), encoding="utf-8")


diagnostics_panel = DiagnosticsPanel()