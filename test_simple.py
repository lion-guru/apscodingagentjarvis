"""
Simple test to verify the task runner can load and execute
"""
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("Testing task runner imports...")

try:
    from agent import build_system_prompt, create_tool_registry
    print("[OK] Agent imports successful")
except Exception as e:
    print(f"[ERROR] Agent imports failed: {e}")
    sys.exit(1)

try:
    from task_queue_runner import load_tasks, save_tasks
    print("[OK] Task runner imports successful")
except Exception as e:
    print(f"[ERROR] Task runner imports failed: {e}")
    sys.exit(1)

try:
    tasks = load_tasks()
    print(f"[OK] Loaded {len(tasks)} tasks")
except Exception as e:
    print(f"[ERROR] Failed to load tasks: {e}")
    sys.exit(1)

print("\n[SUCCESS] All basic tests passed!")
print("The system is ready for autonomous task execution.")
