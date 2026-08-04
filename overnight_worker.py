"""
DevMind Overnight Worker — Autonomous Background Task Loop & Auto-Restart Recovery
Executes long-running coding tasks while the user sleeps, with auto-resume on PC reboot.
"""
import os
import json
import time
from pathlib import Path

QUEUE_FILE = Path.home() / ".devmind" / "overnight_queue.json"

class OvernightTaskWorker:
    def __init__(self):
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not QUEUE_FILE.exists():
            QUEUE_FILE.write_text(json.dumps({"tasks": [], "history": []}, indent=2), encoding="utf-8")

    def add_task(self, prompt: str, category: str = "coding") -> dict:
        """Add task to overnight execution queue."""
        try:
            data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            task_id = len(data["tasks"]) + len(data["history"]) + 1
            task_item = {
                "id": task_id,
                "prompt": prompt,
                "category": category,
                "status": "pending",
                "created_at": time.time()
            }
            data["tasks"].append(task_item)
            QUEUE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"status": "ok", "task": task_item}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_queue(self) -> dict:
        """Get overnight task queue and execution status."""
        try:
            if QUEUE_FILE.exists():
                return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            return {"tasks": [], "history": []}
        except Exception as e:
            return {"error": str(e)}

    def setup_startup_recovery(self) -> dict:
        """Generate Windows startup auto-restart script so DevMind resumes automatically if PC reboots."""
        try:
            startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            bat_path = startup_dir / "Start_DevMind_Jarvis_Autonomy.bat"
            
            script_content = f"""@echo off
title DevMind JARVIS Auto-Recovery Startup
cd /d "E:\\coding-assistant"
echo [JARVIS] PC Reboot Detected — Resuming DevMind Autonomous Agent Server...
call START_SERVER.bat
"""
            bat_path.write_text(script_content, encoding="utf-8")
            return {"status": "ok", "startup_script": str(bat_path)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global Instance
overnight_worker = OvernightTaskWorker()
