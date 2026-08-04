import os
import requests

api_key = "AIzaSyCBNZupHm-q1iLcmeI2MzkzgT91YydOTBY"
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
