"""
DevMind Steering Engine
Persistent coding standards, project rules, and instructions.
Inspired by Kiro's steering files that persist across sessions.
"""
import json
from pathlib import Path
from datetime import datetime

STEERING_DIR = Path.home() / ".devmind" / "steering"

class SteeringEngine:
    def __init__(self):
        STEERING_DIR.mkdir(parents=True, exist_ok=True)

    def create_steering_file(self, name: str, content: str,
                              scope: str = "project", language: str = None) -> dict:
        """Create a steering file with coding rules."""
        steering = {
            "name": name,
            "content": content,
            "scope": scope,
            "language": language,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        steering_file = STEERING_DIR / f"{name}.json"
        steering_file.write_text(json.dumps(steering, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "steering": steering}

    def get_steering_file(self, name: str) -> dict:
        """Get a steering file by name."""
        steering_file = STEERING_DIR / f"{name}.json"
        if not steering_file.exists():
            return {"status": "error", "error": f"Steering file '{name}' not found"}
        return {"status": "ok", "steering": json.loads(steering_file.read_text(encoding="utf-8"))}

    def list_steering_files(self) -> list[dict]:
        """List all steering files."""
        files = []
        if STEERING_DIR.exists():
            for f in STEERING_DIR.glob("*.json"):
                try:
                    s = json.loads(f.read_text(encoding="utf-8"))
                    files.append({
                        "name": s.get("name", f.stem),
                        "scope": s.get("scope", "project"),
                        "language": s.get("language"),
                        "updated_at": s.get("updated_at", ""),
                    })
                except Exception:
                    pass
        return files

    def update_steering_file(self, name: str, content: str = None,
                               scope: str = None, language: str = None) -> dict:
        """Update an existing steering file."""
        result = self.get_steering_file(name)
        if result.get("status") != "ok":
            return result

        steering = result["steering"]
        if content is not None:
            steering["content"] = content
        if scope is not None:
            steering["scope"] = scope
        if language is not None:
            steering["language"] = language
        steering["updated_at"] = datetime.now().isoformat()

        steering_file = STEERING_DIR / f"{name}.json"
        steering_file.write_text(json.dumps(steering, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "steering": steering}

    def delete_steering_file(self, name: str) -> dict:
        """Delete a steering file."""
        steering_file = STEERING_DIR / f"{name}.json"
        if not steering_file.exists():
            return {"status": "error", "error": f"Steering file '{name}' not found"}
        steering_file.unlink()
        return {"status": "ok", "message": f"Steering file '{name}' deleted"}

    def get_all_rules(self) -> list[str]:
        """Get all rules from all steering files."""
        rules = []
        for s in self.list_steering_files():
            steering = self.get_steering_file(s["name"])
            if steering.get("status") == "ok":
                content = steering["steering"].get("content", "")
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        rules.append(line)
        return rules

    def requires_approval(self, action: str, context: dict = None) -> bool:
        """Check if an action requires human approval (dangerous operations)"""
        dangerous_patterns = [
            "sudo", "rm -rf", "git push -f", "git reset --hard",
            "chmod 777", "chown", "systemctl", "shutdown", "reboot",
            "format", "mkfs", "dd if=", "> /dev/",
        ]
        action_lower = action.lower()
        for pattern in dangerous_patterns:
            if pattern in action_lower:
                return True
        
        tool = (context or {}).get("tool", "").lower()
        if tool in ["bash", "terminal", "run_command"]:
            params = (context or {}).get("params", {})
            cmd = params.get("command", "").lower()
            for pattern in dangerous_patterns:
                if pattern in cmd:
                    return True
        
        return False


steering_engine = SteeringEngine()

# Module-level wrapper functions for server.py compatibility
def create_steering_file(name, content, scope="project", language=None):
    return steering_engine.create_steering_file(name, content, scope, language)

def list_steering_files():
    return steering_engine.list_steering_files()

def get_steering_file(name):
    return steering_engine.get_steering_file(name)

def update_steering_file(name, content=None, scope=None, language=None):
    return steering_engine.update_steering_file(name, content, scope, language)

def delete_steering_file(name):
    return steering_engine.delete_steering_file(name)

def requires_approval(action, context=None):
    return steering_engine.requires_approval(action, context)