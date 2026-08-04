import os
import httpx
from agent import load_env_file

load_env_file()
api_key = os.getenv("OPENROUTER_API_KEY")

log_lines = []
log_lines.append(f"Testing OPENROUTER_API_KEY: {api_key}")

models_to_test = [
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "meta-llama/llama-3.2-1b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "deepseek/deepseek-r1:free"
]

url = "https://openrouter.ai/api/v1/chat/completions"

for model_name in models_to_test:
    log_lines.append(f"\n--- Testing Model: {model_name} ---")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:7860",
        "X-OpenRouter-Title": "DevMind Local AI Agent",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        log_lines.append(f"Status Code: {r.status_code}")
        log_lines.append(f"Response: {r.text}")
    except Exception as e:
        log_lines.append(f"Exception: {e}")

with open("e:\\coding-assistant\\openrouter_test_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

print("Diagnosis completed. Results saved to openrouter_test_log.txt")
