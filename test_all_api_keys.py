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

results = {}

print("==================================================")
print("🔑 TESTING ALL CONFIGURED API KEYS")
print("==================================================")

# 1. Gemini API Key Test
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Hi"}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        if r.status_code == 200:
            results["GEMINI_API_KEY"] = {"status": "WORKING ✅", "code": 200}
        else:
            results["GEMINI_API_KEY"] = {"status": f"FAILED ❌ ({r.status_code})", "response": r.json() if "json" in r.headers.get("content-type", "") else r.text[:200]}
    except Exception as e:
        results["GEMINI_API_KEY"] = {"status": f"ERROR ❌", "error": str(e)}
else:
    results["GEMINI_API_KEY"] = {"status": "NOT SET"}

# 2. OpenRouter API Key Test
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
    payload = {"model": "google/gemma-2-9b-it:free", "messages": [{"role": "user", "content": "Hi"}]}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        if r.status_code == 200:
            results["OPENROUTER_API_KEY"] = {"status": "WORKING ✅", "code": 200}
        else:
            results["OPENROUTER_API_KEY"] = {"status": f"FAILED ❌ ({r.status_code})", "response": r.json() if "json" in r.headers.get("content-type", "") else r.text[:200]}
    except Exception as e:
        results["OPENROUTER_API_KEY"] = {"status": f"ERROR ❌", "error": str(e)}
else:
    results["OPENROUTER_API_KEY"] = {"status": "NOT SET"}

# 3. OpenAI API Key Test
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {openai_key}"}
    try:
        r = httpx.get(url, headers=headers, timeout=10.0)
        if r.status_code == 200:
            results["OPENAI_API_KEY"] = {"status": "WORKING ✅", "code": 200}
        else:
            results["OPENAI_API_KEY"] = {"status": f"FAILED ❌ ({r.status_code})", "response": r.json() if "json" in r.headers.get("content-type", "") else r.text[:200]}
    except Exception as e:
        results["OPENAI_API_KEY"] = {"status": f"ERROR ❌", "error": str(e)}
else:
    results["OPENAI_API_KEY"] = {"status": "NOT SET"}

# 4. Anthropic API Key Test
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key:
    url = "https://api.anthropic.com/v1/messages"
    headers = {"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    payload = {"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if r.status_code == 200:
            results["ANTHROPIC_API_KEY"] = {"status": "WORKING ✅", "code": 200}
        else:
            results["ANTHROPIC_API_KEY"] = {"status": f"FAILED ❌ ({r.status_code})", "response": r.json() if "json" in r.headers.get("content-type", "") else r.text[:200]}
    except Exception as e:
        results["ANTHROPIC_API_KEY"] = {"status": f"ERROR ❌", "error": str(e)}
else:
    results["ANTHROPIC_API_KEY"] = {"status": "NOT SET"}

print(json.dumps(results, indent=2))
print("==================================================")
with open("E:/coding-assistant/api_key_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
