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

gemini_key = os.getenv("GEMINI_API_KEY")
print("GEMINI_KEY:", gemini_key)

for model in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "hi"}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        print(f"Model {model}: Status {r.status_code}")
        if r.status_code == 200:
            print(" -> Success:", r.json()["candidates"][0]["content"]["parts"][0]["text"][:50])
        else:
            print(" -> Error:", r.text[:150])
    except Exception as e:
        print(f" -> Exception: {e}")
