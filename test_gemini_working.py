import os
from agent import load_env_file, dispatch_single_model

load_env_file()

print("Testing Gemini 1.5 Flash via dispatch_single_model...")
messages = [{"role": "user", "content": "Write a 1-line hello message."}]

try:
    res = dispatch_single_model(messages, "gemini-1.5-flash")
    print(f"\n✅ GEMINI SUCCESS: {res}")
    with open("e:\\coding-assistant\\gemini_status.txt", "w") as f:
        f.write(f"SUCCESS: {res}")
except Exception as e:
    print(f"\n❌ GEMINI ERROR: {e}")
    with open("e:\\coding-assistant\\gemini_status.txt", "w") as f:
        f.write(f"ERROR: {e}")
