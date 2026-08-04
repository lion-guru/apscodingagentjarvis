import httpx
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY", "")

models_to_test = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
results = []

results.append("==================================================")
results.append(f"🧪 TESTING NEW GEMINI API KEY: {key[:15]}...")
results.append("==================================================")

for m in models_to_test:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Hello, answer OK"}]}]}
    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        if r.status_code == 200:
            resp_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            results.append(f"🟢 Model '{m}': WORKING 100% ✅ -> Response: {resp_text}")
        else:
            results.append(f"🔴 Model '{m}': HTTP {r.status_code} -> {r.text[:200]}")
    except Exception as e:
        results.append(f"🔴 Model '{m}': ERROR -> {e}")

results.append("==================================================")
text = "\n".join(results)
print(text)

with open("E:/coding-assistant/new_key_status.txt", "w", encoding="utf-8") as f:
    f.write(text)
