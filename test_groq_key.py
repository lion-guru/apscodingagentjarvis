import os
import json
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

output = []
output.append("==================================================")
output.append("🔑 LIVE GROQ & API KEY VERIFICATION TEST")
output.append("==================================================")

# Test Groq API Key
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "Say OK"}]}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        if r.status_code == 200:
            res_content = r.json()["choices"][0]["message"]["content"].strip()
            output.append(f"⚡ GROQ_API_KEY: WORKING 100% ✅ (Response: '{res_content}')")
        else:
            output.append(f"🔴 GROQ_API_KEY: FAILED ({r.status_code}) - {r.text[:200]}")
    except Exception as e:
        output.append(f"🔴 GROQ_API_KEY: ERROR - {e}")
else:
    output.append("⚪ GROQ_API_KEY: NOT SET")

output.append("==================================================")
res_text = "\n".join(output)
print(res_text)

with open("E:/coding-assistant/groq_test_result.txt", "w", encoding="utf-8") as f:
    f.write(res_text)
