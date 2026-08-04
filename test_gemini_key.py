import os
import httpx
from agent import load_env_file

load_env_file()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing GEMINI_API_KEY: {api_key[:10]}...{api_key[-5:] if api_key else 'NONE'}")

models_to_test = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

for m in models_to_test:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Say hello from Gemini!"}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        print(f"Model: {m} -> Status Code: {r.status_code}")
        if r.status_code == 200:
            res = r.json()
            content = res["candidates"][0]["content"]["parts"][0]["text"]
            print(f"  ✅ SUCCESS! Response: {content.strip()}")
        else:
            print(f"  ❌ Failed: {r.text[:200]}")
    except Exception as e:
        print(f"  ❌ Exception on {m}: {e}")
