"""
DevMind Spaces Manager
Context bundles for organizing agent sessions, PRs, and files.
Inspired by Devin Desktop's Spaces feature.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

SPACES_DIR = Path.home() / ".devmind" / "spaces"

class SpacesManager:
    def __init__(self):
        SPACES_DIR.mkdir(parents=True, exist_ok=True)

    def create_space(self, name: str, description: str = "",
                     files: list[str] = None, agents: list[str] = None) -> dict:
        """Create a new space (context bundle)."""
        space_id = str(uuid.uuid4())[:8]
        space = {
            "id": space_id,
            "name": name,
            "description": description,
            "files": files or [],
            "agents": agents or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        space_file = SPACES_DIR / f"{space_id}.json"
        space_file.write_text(json.dumps(space, indent=2, default=str), encoding="utf-8")
        return {"status": "ok", "space": space}

    def get_space(self, space_id: str) -> dict:
        """Get a space by ID."""
        space_file = SPACES_DIR / f"{space_id}.json"
        if not space_file.exists():
            return {"status": "error", "error": f"Space '{space_id}' not found"}
        return {"status": "ok", "space": json.loads(space_file.read_text(encoding="utf-8"))}

    def list_spaces(self) -> list[dict]:
        """List all spaces."""
        spaces = []
        if SPACES_DIR.exists():
            for f in SPACES_DIR.glob("*.json"):
                try:
                    space = json.loads(f.read_text(encoding="utf-8"))
                    spaces.append({
                        "id": space.get("id", f.stem),
                        "name": space.get("name", f.stem),
                        "description": space.get("description", ""),
                        "file_count": len(space.get("files", [])),
                        "agent_count": len(space.get("agents", [])),
                        "updated_at": space.get("updated_at", ""),
                    })
                except Exception:
                    pass
        return spaces

    def add_file_to_space(self, space_id: str, file_path: str) -> dict:
        """Add a file to a space."""
        result = self.get_space(space_id)
        if result.get("status") != "ok":
            return result

        space = result["space"]
        if file_path not in space["files"]:
            space["files"].append(file_path)
            space["updated_at"] = datetime.now().isoformat()
            self._save_space(space)
        return {"status": "ok", "space": space}

    def add_agent_to_space(self, space_id: str, agent_id: str) -> dict:
        """Add an agent to a space."""
        result = self.get_space(space_id)
        if result.get("status") != "ok":
            return result

        space = result["space"]
        if agent_id not in space["agents"]:
            space["agents"].append(agent_id)
            space["updated_at"] = datetime.now().isoformat()
            self._save_space(space)
        return {"status": "ok", "space": space}

    def delete_space(self, space_id: str) -> dict:
        """Delete a space."""
        space_file = SPACES_DIR / f"{space_id}.json"
        if not space_file.exists():
            return {"status": "error", "error": f"Space '{space_id}' not found"}
        space_file.unlink()
        return {"status": "ok", "message": f"Space '{space_id}' deleted"}

    def _save_space(self, space: dict):
        """Save space to disk."""
        space_file = SPACES_DIR / f"{space['id']}.json"
        space_file.write_text(json.dumps(space, indent=2, default=str), encoding="utf-8")


spaces_manager = SpacesManager()


def create_space(name: str, description: str = "", files: list = None, agents: list = None) -> dict:
    return spaces_manager.create_space(name, description, files, agents)

def get_space(space_id: str) -> dict:
    return spaces_manager.get_space(space_id)

def list_spaces() -> list:
    return spaces_manager.list_spaces()

def add_file_to_space(space_id: str, file_path: str) -> dict:
    return spaces_manager.add_file_to_space(space_id, file_path)

def add_agent_to_space(space_id: str, agent_id: str) -> dict:
    return spaces_manager.add_agent_to_space(space_id, agent_id)

def delete_space(space_id: str) -> dict:
    return spaces_manager.delete_space(space_id)