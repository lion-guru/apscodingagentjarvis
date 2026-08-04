import os
import httpx
from agent import load_env_file

load_env_file()
api_key = os.getenv("OPENROUTER_API_KEY")

print(f"Loaded OPENROUTER_API_KEY: {api_key[:15]}...{api_key[-10:] if api_key else 'NONE'}")

if not api_key:
    print("❌ OPENROUTER_API_KEY is missing!")
    exit(1)

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen/qwen-2.5-coder-32b-instruct:free",
    "messages": [{"role": "user", "content": "Say hello from OpenRouter fast API!"}]
}

try:
    print("Connecting to OpenRouter API...")
    r = httpx.post(url, json=payload, headers=headers, timeout=15.0)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        res = r.json()
        content = res["choices"][0]["message"]["content"]
        print("✅ OpenRouter API Working Successfully!")
        print(f"Response: {content}")
    else:
        print(f"Error Response: {r.text}")
except Exception as e:
    print(f"Exception connecting to OpenRouter: {e}")
