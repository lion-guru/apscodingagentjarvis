r"""
DevMind — Autonomous Task Queue Runner (Sleep Mode)
Runs queued coding tasks autonomously against the workspace (e.g. c:\xampp\htdocs\apsdreamhome).
"""
import os
import sys
import json
import time
import argparse
import io
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for Unicode/emoji support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from agent import (
    build_system_prompt, create_tool_registry, execute_tool,
    extract_tool_calls, remove_tool_calls, ollama_chat,
    DEFAULT_MODEL, DEFAULT_WORKSPACE, translate_to_english,
    compact_history, backup_file
)

TASKS_FILE = Path("tasks.json")
LOG_FILE   = Path("task_runner.log")

DEFAULT_TASKS = [
    {
        "id": 1,
        "title": "Inspect Playwright & Test Setup",
        "instruction": r"Scan playwright.config.js and test files in c:\xampp\htdocs\apsdreamhome and verify all configurations are clean.",
        "status": "pending"
    },
    {
        "id": 2,
        "title": "Check Syntax Diagnostics",
        "instruction": "Diagnose JavaScript, PHP, and Python files in the workspace for any hidden syntax or structure errors.",
        "status": "pending"
    }
]

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def load_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text(json.dumps({"tasks": DEFAULT_TASKS}, indent=2), encoding="utf-8")
        log(f"Created default tasks file at {TASKS_FILE.absolute()}")
        return DEFAULT_TASKS
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        return data.get("tasks", DEFAULT_TASKS)
    except Exception as e:
        log(f"Error loading tasks.json: {e}")
        return []

def save_tasks(tasks: list[dict]):
    data = {"tasks": tasks}
    TASKS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def run_single_task(task: dict, model: str, cwd: str, max_steps: int = 12) -> bool:
    log(f"[START] Task #{task['id']}: {task['title']}")
    log(f"Instruction: {task['instruction']}")
    
    tools = create_tool_registry()
    system_prompt = build_system_prompt(cwd, tools)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[AUTONOMOUS TASK] Task ID {task['id']}: {task['instruction']}"}
    ]
    
    step = 0
    success = False
    
    while step < max_steps:
        step += 1
        log(f"--- Step {step}/{max_steps} ---")
        
        messages = compact_history(messages, model)
        
        try:
            response = ollama_chat(messages, model=model)
        except Exception as e:
            log(f"[ERROR] Error communicating with LLM ({model}): {e}")
            time.sleep(3)
            continue
            
        messages.append({"role": "assistant", "content": response})
        tool_calls = extract_tool_calls(response)
        clean_text = remove_tool_calls(response)
        
        if clean_text.strip():
            log(f"[AI Output]\n{clean_text[:400]}")
            
        if not tool_calls:
            log("[SUCCESS] No further tool calls requested. Task thought loop completed.")
            success = True
            break
            
        for call in tool_calls:
            t_name = call.get("tool")
            t_params = call.get("params", {})
            log(f"[TOOL] Executing Tool: {t_name} with params: {t_params}")
            
            res = execute_tool(tools, t_name, t_params)
            log(f"[RESULT] Tool Result ({t_name}): success={res.success}\n{res.output[:300]}")
            
            messages.append({
                "role": "user",
                "content": f"[TOOL RESULT for {t_name}]:\n{res.output}"
            })
            
    return success

def main():
    parser = argparse.ArgumentParser(description="DevMind Autonomous Task Queue Runner")
    parser.add_argument("--cwd", type=str, default=str(DEFAULT_WORKSPACE), help="Target workspace path")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name to use")
    parser.add_argument("--task", type=str, default=None, help="Run a single instruction directly")
    args = parser.parse_args()

    os.environ["DEVMIND_CWD"] = args.cwd
    log(f"Target Workspace CWD: {args.cwd}")
    log(f"Selected Model: {args.model}")

    if args.task:
        custom_task = {
            "id": 999,
            "title": "Custom CLI Task",
            "instruction": args.task,
            "status": "pending"
        }
        res = run_single_task(custom_task, args.model, args.cwd)
        log(f"Task finished with result: {'SUCCESS' if res else 'FINISHED'}")
        return

    tasks = load_tasks()
    pending = [t for t in tasks if t.get("status") == "pending"]
    log(f"Found {len(pending)} pending tasks in queue out of {len(tasks)} total tasks.")

    for task in tasks:
        if task.get("status") != "pending":
            continue
            
        task["status"] = "in_progress"
        task["started_at"] = datetime.now().isoformat()
        save_tasks(tasks)
        
        try:
            ok = run_single_task(task, args.model, args.cwd)
            task["status"] = "completed" if ok else "failed"
        except Exception as e:
            log(f"[ERROR] Exception running task #{task['id']}: {e}")
            task["status"] = "failed"
            task["error"] = str(e)
            
        task["completed_at"] = datetime.now().isoformat()
        save_tasks(tasks)
        
        log(f"Task #{task['id']} finished with status: {task['status']}")
        time.sleep(2)

    log("[SUCCESS] All queued tasks processed!")

if __name__ == "__main__":
    main()
