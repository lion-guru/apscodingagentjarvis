import os
import requests
from pathlib import Path

# Load .env manually
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

results = {}

def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return "No API Key"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Say 'OK'"}], "max_tokens": 10}
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=10)
        return f"Status {r.status_code}: {r.json().get('choices', [{}])[0].get('message', {}).get('content', r.text).strip()}"
    except Exception as e: return f"Error: {e}"

def test_anthropic():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key: return "No API Key"
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    payload = {"model": "claude-3-haiku-20240307", "messages": [{"role": "user", "content": "Say 'OK'"}], "max_tokens": 10}
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=10)
        return f"Status {r.status_code}: {r.json().get('content', [{}])[0].get('text', r.text).strip()}"
    except Exception as e: return f"Error: {e}"

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return "No API Key"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Say 'OK'"}]}]}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return f"Status 200: {r.json()['candidates'][0]['content']['parts'][0]['text'].strip()}"
        return f"Status {r.status_code}: {r.text}"
    except Exception as e: return f"Error: {e}"

def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return "No API Key"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "google/gemma-2-9b-it", "messages": [{"role": "user", "content": "Say 'OK'"}]}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            return f"Status 200: {r.json()['choices'][0]['message']['content'].strip()}"
        return f"Status {r.status_code}: {r.text}"
    except Exception as e: return f"Error: {e}"

print("--- API TESTING RESULTS ---")
print("1. OpenAI (gpt-4o-mini):", test_openai())
print("2. Anthropic (claude-3-haiku):", test_anthropic())
print("3. Gemini (gemini-1.5-flash):", test_gemini())
print("4. OpenRouter (gemma-2-9b):", test_openrouter())
print("---------------------------")
