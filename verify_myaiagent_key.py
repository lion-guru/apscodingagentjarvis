import os
import httpx
from agent import load_env_file

load_env_file()
api_key = os.getenv("OPENROUTER_API_KEY")

print("==================================================")
print(f"Testing Active OpenRouter Key: {api_key[:20]}...{api_key[-5:]}")
print("==================================================")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "HTTP-Referer": "http://localhost:7860",
    "X-OpenRouter-Title": "DevMind Local AI Agent",
    "Content-Type": "application/json"
}

models_to_test = [
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "meta-llama/llama-3.2-1b-instruct:free",
    "google/gemma-2-9b-it:free"
]

for model_name in models_to_test:
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Return 'OK' if working."}]
    }
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=12.0)
        print(f"Model: {model_name} -> Status: {r.status_code}")
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            print(f"  ✅ SUCCESS: {content.strip()}")
            break
        else:
            print(f"  ⚠️ Error: {r.text[:150]}")
    except Exception as e:
        print(f"  ❌ Exception: {e}")
