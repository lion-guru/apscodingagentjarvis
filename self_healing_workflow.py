"""
Self-Healing Workflow System for Jarvis/DevMind
Inspired by santhanam-15/Jarvis - Auto-recovery on failure
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import time
import subprocess

WORKFLOW_LOG = Path(".devmind") / "workflow_failures.json"
WORKFLOW_LOG.parent.mkdir(parents=True, exist_ok=True)

class SelfHealingWorkflow:
    def __init__(self):
        self.failure_patterns = {}
        self.healing_strategies = {}
        self.load_failure_data()

    def load_failure_data(self):
        """Load failure patterns and healing strategies"""
        if WORKFLOW_LOG.exists():
            try:
                with open(WORKFLOW_LOG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.failure_patterns = data.get("failure_patterns", {})
                    self.healing_strategies = data.get("healing_strategies", {})
            except Exception:
                pass

    def save_failure_data(self):
        """Save failure patterns and healing strategies"""
        with open(WORKFLOW_LOG, 'w', encoding='utf-8') as f:
            json.dump({
                "failure_patterns": self.failure_patterns,
                "healing_strategies": self.healing_strategies
            }, f, indent=2)

    def record_failure(self, task: str, error: str, context: str = ""):
        """Record a failure pattern"""
        # Extract error type
        error_type = self.classify_error(error)
        
        if error_type not in self.failure_patterns:
            self.failure_patterns[error_type] = []
        
        failure_record = {
            "task": task,
            "error": error,
            "context": context,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "occurrences": 1
        }
        
        # Check if similar failure exists
        for existing in self.failure_patterns[error_type]:
            if existing["task"] == task and existing["error"] == error:
                existing["occurrences"] += 1
                existing["timestamp"] = failure_record["timestamp"]
                self.save_failure_data()
                return
        
        self.failure_patterns[error_type].append(failure_record)
        self.save_failure_data()

    def classify_error(self, error: str) -> str:
        """Classify error type for pattern matching"""
        error_lower = error.lower()
        
        if "syntax" in error_lower or "parse" in error_lower:
            return "syntax_error"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission_error"
        elif "not found" in error_lower or "does not exist" in error_lower:
            return "not_found_error"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "network_error"
        elif "sql" in error_lower or "database" in error_lower:
            return "database_error"
        elif "memory" in error_lower or "out of" in error_lower:
            return "resource_error"
        else:
            return "unknown_error"

    def generate_healing_strategy(self, error_type: str, task: str) -> str:
        """Generate a healing strategy for a given error type"""
        # Pre-defined healing strategies
        strategies = {
            "syntax_error": "Review the code for syntax errors, check brackets, quotes, and semicolons",
            "permission_error": "Check file permissions, run with elevated privileges if needed",
            "not_found_error": "Verify the file or resource exists, check the path",
            "timeout_error": "Increase timeout duration, check network connectivity",
            "network_error": "Check internet connection, retry the operation",
            "database_error": "Check database connection, verify SQL syntax",
            "resource_error": "Close unnecessary applications, increase available memory",
            "unknown_error": "Review error logs, try a different approach"
        }
        
        base_strategy = strategies.get(error_type, strategies["unknown_error"])
        
        # Add task-specific advice
        task_lower = task.lower()
        if "file" in task_lower:
            base_strategy += ". Ensure file paths are correct and files exist."
        elif "database" in task_lower:
            base_strategy += ". Verify database credentials and table structure."
        elif "api" in task_lower:
            base_strategy += ". Check API endpoints and authentication."
        
        return base_strategy

    def attempt_healing(self, task: str, error: str, context: str = "") -> Dict:
        """Attempt to heal a failed task"""
        error_type = self.classify_error(error)
        
        # Record the failure
        self.record_failure(task, error, context)
        
        # Generate healing strategy
        strategy = self.generate_healing_strategy(error_type, task)
        
        # Check if we have a healing strategy for this error type
        if error_type in self.healing_strategies:
            # Use existing strategy
            healing_actions = self.healing_strategies[error_type]
            return {
                "healed": True,
                "strategy": strategy,
                "actions": healing_actions,
                "error_type": error_type
            }
        else:
            # Generate new strategy
            healing_actions = self.generate_healing_actions(error_type, task)
            self.healing_strategies[error_type] = healing_actions
            self.save_failure_data()
            
            return {
                "healed": False,
                "strategy": strategy,
                "actions": healing_actions,
                "error_type": error_type,
                "requires_manual_intervention": True
            }

    def generate_healing_actions(self, error_type: str, task: str) -> List[str]:
        """Generate specific healing actions"""
        actions = []
        
        if error_type == "syntax_error":
            actions = [
                "Run syntax checker on the file",
                "Review line numbers in error message",
                "Check for missing brackets or quotes"
            ]
        elif error_type == "permission_error":
            actions = [
                "Check file permissions",
                "Run with elevated privileges if safe",
                "Verify user has necessary access"
            ]
        elif error_type == "not_found_error":
            actions = [
                "Verify file or resource exists",
                "Check path spelling and case",
                "Ensure working directory is correct"
            ]
        elif error_type == "timeout_error":
            actions = [
                "Increase timeout duration",
                "Check network connectivity",
                "Retry the operation"
            ]
        elif error_type == "network_error":
            actions = [
                "Check internet connection",
                "Verify API endpoint is accessible",
                "Retry with exponential backoff"
            ]
        elif error_type == "database_error":
            actions = [
                "Check database connection",
                "Verify SQL syntax",
                "Check table and column names"
            ]
        else:
            actions = [
                "Review error logs",
                "Try alternative approach",
                "Check for missing dependencies"
            ]
        
        return actions

    def get_failure_report(self) -> Dict:
        """Get report of all failures and healing strategies"""
        return {
            "failure_patterns": self.failure_patterns,
            "healing_strategies": self.healing_strategies,
            "total_failures": sum(len(patterns) for patterns in self.failure_patterns.values()),
            "error_types": list(self.failure_patterns.keys())
        }

# Global self-healing workflow instance
self_healing_workflow = SelfHealingWorkflow()

def attempt_heal(task: str, error: str, context: str = "") -> Dict:
    """Public interface to attempt healing on a failed task"""
    return self_healing_workflow.attempt_healing(task, error, context)

def get_failure_report() -> Dict:
    """Get failure report"""
    return self_healing_workflow.get_failure_report()

if __name__ == "__main__":
    # Test self-healing workflow
    print("Testing Self-Healing Workflow")
    print("=" * 50)
    
    # Simulate a failure
    result = attempt_heal(
        task="Read file config.json",
        error="FileNotFoundError: [Errno 2] No such file or directory: 'config.json'",
        context="Configuration loading"
    )
    
    print(f"Healing Attempt:")
    print(f"  Healed: {result['healed']}")
    print(f"  Error Type: {result['error_type']}")
    print(f"  Strategy: {result['strategy']}")
    print(f"  Actions: {result['actions']}")
    
    # Get failure report
    report = get_failure_report()
    print(f"\nFailure Report:")
    print(f"  Total Failures: {report['total_failures']}")
    print(f"  Error Types: {report['error_types']}")
