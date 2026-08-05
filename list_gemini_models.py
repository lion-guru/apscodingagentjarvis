import os
import requests

api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set")
    exit(1)
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print("Available Models:")
        for m in models:
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                print(f"- {m['name']} (Version: {m.get('version', 'unknown')})")
    else:
        print(f"Error fetching models: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
