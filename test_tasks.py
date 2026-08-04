"""
Simple test to verify task loading
"""
import json
from pathlib import Path

TASKS_FILE = Path("tasks.json")

print("Testing task loading...")

if not TASKS_FILE.exists():
    print(f"[ERROR] Tasks file not found: {TASKS_FILE}")
    exit(1)

try:
    data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    print(f"[OK] Loaded {len(tasks)} tasks")
    
    for task in tasks:
        print(f"  - Task {task['id']}: {task['title']} ({task.get('status', 'unknown')})")
    
    print("\n[SUCCESS] Task loading works correctly!")
except Exception as e:
    print(f"[ERROR] Failed to load tasks: {e}")
    exit(1)
