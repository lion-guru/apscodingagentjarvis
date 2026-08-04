import os
import httpx
from agent import load_env_file

load_env_file()
api_key = os.getenv("GEMINI_API_KEY")

log_lines = []
log_lines.append(f"Testing GEMINI_API_KEY: {api_key[:12]}...{api_key[-5:] if api_key else 'NONE'}")

models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

for m in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Hello, write a 1-sentence response."}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        log_lines.append(f"\nModel: {m}")
        log_lines.append(f"Status Code: {r.status_code}")
        log_lines.append(f"Response Body: {r.text[:300]}")
    except Exception as e:
        log_lines.append(f"\nModel: {m} Exception: {e}")

with open("e:\\coding-assistant\\gemini_test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

print("Gemini diagnosis complete.")
