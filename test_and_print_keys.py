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
output.append("🔑 API KEY DIAGNOSTIC TEST RESULTS")
output.append("==================================================")

# 1. Gemini API Key
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Say OK"}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        if r.status_code == 200:
            output.append("🟢 GEMINI_API_KEY: WORKING 100% ✅ (Response: 200 OK)")
        else:
            output.append(f"🔴 GEMINI_API_KEY: FAILED ({r.status_code}) - {r.text[:200]}")
    except Exception as e:
        output.append(f"🔴 GEMINI_API_KEY: ERROR - {e}")
else:
    output.append("⚪ GEMINI_API_KEY: NOT SET")

# 2. OpenRouter API Key
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
    payload = {"model": "google/gemma-2-9b-it:free", "messages": [{"role": "user", "content": "Say OK"}]}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        if r.status_code == 200:
            output.append("🟢 OPENROUTER_API_KEY: WORKING 100% ✅ (Response: 200 OK)")
        else:
            output.append(f"🔴 OPENROUTER_API_KEY: FAILED ({r.status_code}) - {r.text[:200]}")
    except Exception as e:
        output.append(f"🔴 OPENROUTER_API_KEY: ERROR - {e}")
else:
    output.append("⚪ OPENROUTER_API_KEY: NOT SET")

# 3. OpenAI API Key
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {openai_key}"}
    try:
        r = httpx.get(url, headers=headers, timeout=10.0)
        if r.status_code == 200:
            output.append("🟢 OPENAI_API_KEY: WORKING 100% ✅ (Response: 200 OK)")
        else:
            output.append(f"🔴 OPENAI_API_KEY: FAILED ({r.status_code}) - {r.text[:200]}")
    except Exception as e:
        output.append(f"🔴 OPENAI_API_KEY: ERROR - {e}")

# 4. Anthropic API Key
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key:
    url = "https://api.anthropic.com/v1/messages"
    headers = {"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    payload = {"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if r.status_code == 200:
            output.append("🟢 ANTHROPIC_API_KEY: WORKING 100% ✅ (Response: 200 OK)")
        else:
            output.append(f"🔴 ANTHROPIC_API_KEY: FAILED ({r.status_code}) - {r.text[:200]}")
    except Exception as e:
        output.append(f"🔴 ANTHROPIC_API_KEY: ERROR - {e}")

output.append("==================================================")
res_text = "\n".join(output)
print(res_text)

with open("E:/coding-assistant/key_status.txt", "w", encoding="utf-8") as f:
    f.write(res_text)
