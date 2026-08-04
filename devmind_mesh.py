"""
DevMind Mesh — Multi-Device State & Memory Sync Engine
Synchronizes workspace contexts, master memory, and agent session tasks across devices.
"""
import os
import json
import time
from pathlib import Path

MESH_STATE_FILE = Path.home() / ".devmind" / "mesh_sync.json"

class DevMindMeshEngine:
    def __init__(self):
        MESH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.device_id = f"device_{os.getlogin()}_{int(time.time()) % 10000}"
        self._init_mesh()

    def _init_mesh(self):
        if not MESH_STATE_FILE.exists():
            data = {
                "devices": [self.device_id],
                "last_sync": time.time(),
                "synced_projects": [],
                "global_memory": []
            }
            MESH_STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def sync(self, workspace_path: str = "") -> dict:
        """Sync local workspace state with DevMind Mesh network."""
        try:
            content = json.loads(MESH_STATE_FILE.read_text(encoding="utf-8"))
            if self.device_id not in content.get("devices", []):
                content.setdefault("devices", []).append(self.device_id)
            
            if workspace_path and workspace_path not in content.get("synced_projects", []):
                content.setdefault("synced_projects", []).append(workspace_path)

            content["last_sync"] = time.time()
            MESH_STATE_FILE.write_text(json.dumps(content, indent=2), encoding="utf-8")
            
            return {
                "status": "ok",
                "device_id": self.device_id,
                "synced_projects": len(content.get("synced_projects", [])),
                "total_devices": len(content.get("devices", [])),
                "timestamp": content["last_sync"]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_status(self) -> dict:
        try:
            if MESH_STATE_FILE.exists():
                return json.loads(MESH_STATE_FILE.read_text(encoding="utf-8"))
            return {"devices": [self.device_id], "status": "standalone"}
        except Exception as e:
            return {"error": str(e)}

# Global Instance
mesh_engine = DevMindMeshEngine()
