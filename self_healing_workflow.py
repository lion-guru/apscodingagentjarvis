"""
Self-Healing Workflow System for DevMind
Inspired by Windsurf Cascade / OpenCode Agent Loops
Auto-recovery on tool execution failures with adaptive replanning
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import subprocess

WORKFLOW_LOG = Path(".devmind") / "workflow_failures.json"
WORKFLOW_LOG.parent.mkdir(parents=True, exist_ok=True)

class ErrorType(Enum):
    SYNTAX_ERROR = "syntax_error"
    PERMISSION_DENIED = "permission_denied"
    FILE_NOT_FOUND = "file_not_found"
    NETWORK_TIMEOUT = "network_timeout"
    TOOL_NOT_FOUND = "tool_not_found"
    COMMAND_FAILED = "command_failed"
    MCP_TOOL_MISSING = "mcp_tool_missing"
    MCP_SERVER_DOWN = "mcp_server_down"
    DEPENDENCY_MISSING = "dependency_missing"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"

class SelfHealingWorkflow:
    def __init__(self):
        self.failure_patterns = {}
        self.healing_strategies = {}
        self.load_failure_data()

    def load_failure_data(self):
        if WORKFLOW_LOG.exists():
            try:
                with open(WORKFLOW_LOG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.failure_patterns = data.get("failure_patterns", {})
                    self.healing_strategies = data.get("healing_strategies", {})
            except Exception:
                pass

    def save_failure_data(self):
        with open(WORKFLOW_LOG, 'w', encoding='utf-8') as f:
            json.dump({
                "failure_patterns": self.failure_patterns,
                "healing_strategies": self.healing_strategies
            }, f, indent=2, default=str)

    def classify_error(self, error: str, context: dict = None) -> ErrorType:
        """Classify error with tool-specific awareness"""
        error_lower = error.lower()
        tool = (context or {}).get("tool", "").lower()

        if "syntaxerror" in error_lower or "parseerror" in error_lower:
            return ErrorType.SYNTAX_ERROR
        if "permission denied" in error_lower or "access is denied" in error_lower:
            return ErrorType.PERMISSION_DENIED
        if "no such file" in error_lower or "file not found" in error_lower:
            return ErrorType.FILE_NOT_FOUND
        if "connection timeout" in error_lower or "timed out" in error_lower or "network is unreachable" in error_lower:
            return ErrorType.NETWORK_TIMEOUT
        if "command not found" in error_lower or "not recognized as" in error_lower:
            return ErrorType.TOOL_NOT_FOUND
        if "module" in error_lower and "not found" in error_lower or "importerror" in error_lower:
            return ErrorType.DEPENDENCY_MISSING
        if "out of memory" in error_lower or "oom" in error_lower:
            return ErrorType.RESOURCE_EXHAUSTED

        if "mcp" in tool:
            if "tool not found" in error_lower:
                return ErrorType.MCP_TOOL_MISSING
            if "server disconnected" in error_lower or "broken pipe" in error_lower:
                return ErrorType.MCP_SERVER_DOWN

        if error_lower.startswith("traceback") or "exception" in error_lower:
            return ErrorType.COMMAND_FAILED

        return ErrorType.UNKNOWN

    def attempt_healing(self, task: str, error: str, context: dict = None) -> Dict[str, Any]:
        """Attempt to heal a failed tool execution with auto-retry params"""
        ctx = context or {}
        error_type = self.classify_error(error, ctx)
        attempt = ctx.get("attempt", 0)
        tool = ctx.get("tool", "unknown")

        self._record_failure(task, error, ctx)

        healing = self._get_healing_strategy(error_type, tool, attempt, ctx)

        return {
            "healed": healing["can_auto_fix"],
            "error_type": error_type.value,
            "strategy": healing["strategy"],
            "adjusted_params": healing.get("adjusted_params"),
            "fallback_advice": healing["fallback_advice"],
            "requires_approval": healing.get("requires_approval", False),
        }

    def _get_healing_strategy(self, error_type: ErrorType, tool: str, attempt: int, ctx: dict) -> dict:
        """Generate tool-specific healing strategy with adjusted params"""
        params = ctx.get("params", {})
        cwd = ctx.get("cwd", os.getcwd())

        if error_type == ErrorType.NETWORK_TIMEOUT:
            timeout = min(params.get("timeout", 60) * (2 ** attempt), 300)
            return {
                "can_auto_fix": True,
                "strategy": f"Retry with increased timeout ({timeout}s) + offline fallback",
                "adjusted_params": {**params, "timeout": timeout},
                "fallback_advice": "Check internet connection, use local cache, or disable proxy",
            }

        if error_type == ErrorType.TOOL_NOT_FOUND:
            missing = self._extract_missing_tool(error_type, ctx)
            if missing:
                install_cmd = f"choco install {missing} -y" if os.name == "nt" else f"sudo apt-get install -y {missing}"
                return {
                    "can_auto_fix": True,
                    "strategy": f"Install missing tool: {missing}",
                    "adjusted_params": {"command": install_cmd, "cwd": cwd},
                    "fallback_advice": f"Install {missing} manually via package manager",
                    "requires_approval": True,
                }
            return {
                "can_auto_fix": False,
                "strategy": "Unknown missing tool",
                "fallback_advice": "Check command spelling and available tools",
            }

        if error_type == ErrorType.PERMISSION_DENIED:
            return {
                "can_auto_fix": False,
                "strategy": "Permission denied - requires elevated privileges",
                "fallback_advice": "Approve elevated execution in DevMind UI",
                "requires_approval": True,
            }

        if error_type == ErrorType.FILE_NOT_FOUND:
            path = params.get("path", params.get("file_path", ""))
            if path:
                parent = os.path.dirname(os.path.abspath(path))
                return {
                    "can_auto_fix": True,
                    "strategy": f"Create missing directories for: {path}",
                    "adjusted_params": {**params, "path": os.path.abspath(path)},
                    "fallback_advice": "Verify path spelling and case sensitivity",
                }
            return {
                "can_auto_fix": False,
                "strategy": "File not found",
                "fallback_advice": "Check file path and ensure it exists",
            }

        if error_type == ErrorType.DEPENDENCY_MISSING:
            module = self._extract_missing_module(error)
            if module:
                pip_cmd = f"pip install {module}"
                return {
                    "can_auto_fix": True,
                    "strategy": f"Install missing dependency: {module}",
                    "adjusted_params": {"command": pip_cmd, "cwd": cwd},
                    "fallback_advice": f"Run: {pip_cmd}",
                }
            return {
                "can_auto_fix": False,
                "strategy": "Missing dependency",
                "fallback_advice": "Install required packages manually",
            }

        if error_type == ErrorType.COMMAND_FAILED:
            if attempt == 0:
                return {
                    "can_auto_fix": True,
                    "strategy": "Retry command (transient failure)",
                    "adjusted_params": params,
                    "fallback_advice": "Check command syntax",
                }
            return {
                "can_auto_fix": False,
                "strategy": "Command failed after retry",
                "fallback_advice": "Review error output and adjust approach",
            }

        if error_type == ErrorType.MCP_SERVER_DOWN:
            server_name = params.get("server_name", "unknown")
            return {
                "can_auto_fix": True,
                "strategy": f"Restart MCP server: {server_name}",
                "adjusted_params": {"action": "restart_mcp_server", "server_name": server_name},
                "fallback_advice": f"Manually restart MCP server: {server_name}",
            }

        if error_type == ErrorType.MCP_TOOL_MISSING:
            return {
                "can_auto_fix": True,
                "strategy": "Re-register MCP tools",
                "adjusted_params": {"action": "refresh_mcp_tools"},
                "fallback_advice": "Check MCP server is running and tools are registered",
            }

        return {
            "can_auto_fix": False,
            "strategy": "Unknown error - manual review required",
            "fallback_advice": "Check error logs and try a different approach",
        }

    def _extract_missing_tool(self, error_type: ErrorType, ctx: dict) -> str:
        error = ctx.get("error", "")
        for part in error.split():
            clean = part.strip(":,.")
            if clean in ["pip", "npm", "git", "docker", "node", "python", "code", "java", "go", "rustc"]:
                return clean
        return ""

    def _extract_missing_module(self, error: str) -> str:
        error_lower = error.lower()
        if "no module named" in error_lower:
            parts = error_lower.split("no module named")
            if len(parts) > 1:
                module = parts[1].strip().strip("'\"").split()[0].strip("'\".")
                return module
        return ""

    def _record_failure(self, task: str, error: str, context: dict):
        error_type = self.classify_error(error, context).value
        if error_type not in self.failure_patterns:
            self.failure_patterns[error_type] = []
        record = {
            "task": task,
            "error": error[:500],
            "context": str(context)[:500],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for existing in self.failure_patterns[error_type]:
            if existing["task"] == task:
                existing["occurrences"] = existing.get("occurrences", 1) + 1
                existing["timestamp"] = record["timestamp"]
                self.save_failure_data()
                return
        record["occurrences"] = 1
        self.failure_patterns[error_type].append(record)
        self.save_failure_data()

    def get_failure_report(self) -> Dict:
        return {
            "failure_patterns": self.failure_patterns,
            "healing_strategies": self.healing_strategies,
            "total_failures": sum(len(p) for p in self.failure_patterns.values()),
            "error_types": list(self.failure_patterns.keys()),
        }

self_healing_workflow = SelfHealingWorkflow()

def attempt_heal(task: str, error: str, context: dict = None) -> Dict[str, Any]:
    return self_healing_workflow.attempt_healing(task, error, context)

def get_failure_report() -> Dict:
    return self_healing_workflow.get_failure_report()

if __name__ == "__main__":
    print("Testing Self-Healing Workflow")
    print("=" * 50)

    result = attempt_heal(
        task="pip install requests",
        error="ERROR: Connection timeout",
        context={"tool": "terminal", "params": {"command": "pip install requests"}, "attempt": 0}
    )
    print(f"Error: {result['error_type']}")
    print(f"Strategy: {result['strategy']}")
    print(f"Auto-fix: {result['healed']}")
    print(f"Adjusted params: {result['adjusted_params']}")
