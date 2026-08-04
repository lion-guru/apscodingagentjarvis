import os
import httpx
from pathlib import Path

# Load .env
env_path = Path("E:/coding-assistant/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"\'')

api_key = os.getenv("GROQ_API_KEY")
org_id = os.getenv("GROQ_ORG_ID")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Groq-Organization": org_id
}
payload = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Hello! Reply with 'GROQ WORKING 100%'."}]
}

try:
    r = httpx.post(url, headers=headers, json=payload, timeout=15.0)
    print("STATUS CODE:", r.status_code)
    if r.status_code == 200:
        print("RESPONSE:", r.json()["choices"][0]["message"]["content"])
    else:
        print("ERROR:", r.text)
except Exception as e:
    print("EXCEPTION:", e)
