import os
import sys
import json
import time

print("==================================================")
print("🚀 REAL LIVE EXECUTION TEST - DEVMIND AI AGENT")
print("==================================================")

from agent import create_tool_registry, build_system_prompt, ollama_chat, extract_tool_calls, execute_tool, remove_tool_calls, DEFAULT_WORKSPACE

cwd = str(DEFAULT_WORKSPACE)
tools = create_tool_registry()
system_prompt = build_system_prompt(cwd, tools)

real_task_instruction = (
    "Perform a real task in the workspace: "
    "1. Count how many .py files are in the root workspace directory. "
    "2. Calculate the total lines of code across all python files in root directory. "
    "3. Create a new file named `real_test_report.json` with keys `total_python_files`, `total_lines`, and `timestamp`. "
    "4. Return a summary of what you did."
)

print(f"📋 Instruction: {real_task_instruction}\n")

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": real_task_instruction}
]

step = 0
max_steps = 6

while step < max_steps:
    step += 1
    print(f"🔄 --- Step {step}/{max_steps} ---")
    
    try:
        response = ollama_chat(messages, model="gemini-2.0-flash")
    except Exception as e:
        print(f"❌ Error during model call: {e}")
        break
        
    messages.append({"role": "assistant", "content": response})
    tool_calls = extract_tool_calls(response)
    clean_text = remove_tool_calls(response)
    
    if clean_text.strip():
        print(f"🤖 [Agent Output]:\n{clean_text.strip()}\n")
        
    if not tool_calls:
        print("✅ Agent loop completed task (no further tool calls).")
        break
        
    for tc in tool_calls:
        t_name = tc.get("tool")
        t_params = tc.get("params", {})
        print(f"🛠️ [Executing Tool]: {t_name} with params: {t_params}")
        
        result = execute_tool(tools, t_name, t_params)
        print(f"📥 [Tool Result ({t_name})]: Success={result.success}\n{result.output[:300]}...\n")
        
        messages.append({
            "role": "user",
            "content": f"[TOOL RESULT for {t_name}]:\n{result.output}"
        })

print("==================================================")
if os.path.exists("real_test_report.json"):
    with open("real_test_report.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print("🎉 REAL EXECUTION TEST PASSED! `real_test_report.json` created:")
    print(json.dumps(data, indent=2))
else:
    print("⚠️ Task finished. Check logs above.")
print("==================================================")
