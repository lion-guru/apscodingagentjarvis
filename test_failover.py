import os
from agent import load_env_file, ollama_chat

load_env_file()

print("Testing ollama_chat failover engine...")
messages = [{"role": "user", "content": "Say 'DevMind Failover Test Passed!'"}]

try:
    response = ollama_chat(messages, model="qwen/qwen-2.5-coder-32b-instruct:free")
    print(f"\n✅ AI Response Received: {response}")
except Exception as e:
    print(f"\n❌ Exception: {e}")
