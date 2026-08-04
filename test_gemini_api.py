import os
import httpx
import json
from pathlib import Path

def test_api():
    print("Testing Gemini API key...")
    api_key = None
    if Path(".env").exists():
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Hello, how are you?"}]}]}
    
    try:
        res = httpx.post(url, json=payload)
        print(f"Status Code: {res.status_code}")
        print("Response JSON:")
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_api()
