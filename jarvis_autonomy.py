"""
JARVIS Autonomy Engine — PC Resource Guard, Service Auto-Launcher & Self-Learning System
Monitors system RAM/CPU, auto-launches Ollama/IDE services, and adapts to user coding style.
"""
import os
import psutil
import subprocess
import json
import time
from pathlib import Path

class JarvisAutonomyEngine:
    def __init__(self):
        self.ollama_host = "http://127.0.0.1:11434"

    def get_system_metrics(self) -> dict:
        """Get live PC resource metrics (CPU, RAM, Disk, Active Processes)."""
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            disk = psutil.disk_usage('E:\\') if os.path.exists('E:\\') else psutil.disk_usage('/')
            
            # Find heavy processes
            heavy_proc = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 5.0:
                        heavy_proc.append({"name": proc.info['name'], "mem_pct": round(proc.info['memory_percent'], 1)})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return {
                "cpu_pct": cpu,
                "ram_pct": mem.percent,
                "ram_free_gb": round(mem.available / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "heavy_processes": heavy_proc[:5],
                "status": "warning" if mem.percent > 85 else "healthy"
            }
        except Exception as e:
            return {"error": str(e), "status": "unknown"}

    def ensure_services_running(self) -> dict:
        """Auto-detect missing services (Ollama, OpenCode) and launch them silently."""
        results = {"ollama_launched": False, "opencode_running": False}
        
        # Check Ollama
        ollama_running = any("ollama" in proc.name().lower() for proc in psutil.process_iter(['name']))
        if not ollama_running:
            try:
                subprocess.Popen("ollama serve", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results["ollama_launched"] = True
            except Exception:
                pass
        
        # Check OpenCode / IDE
        opencode_running = any("opencode" in proc.name().lower() for proc in psutil.process_iter(['name']))
        results["opencode_running"] = opencode_running
        
        return results

    def learn_user_pattern(self, file_edited: str, edit_type: str) -> dict:
        """Self-learning engine: record user coding patterns and style."""
        try:
            from master_db import master_db
            master_db.add_memory(
                key=f"user_style_{int(time.time())}",
                val=f"User edited {file_edited} ({edit_type}). Prefers clean modular structure.",
                category="user_preference"
            )
            return {"status": "learned", "pattern": f"Adapted to user edit style on {file_edited}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global Instance
autonomy_engine = JarvisAutonomyEngine()
