import requests
import json
import os

url = "http://localhost:7860/api/autocomplete"

payload = {
    "model": "gemini-2.0-flash",
    "text_before_cursor": "def calculate_sum(a, b):\n    ",
    "text_after_cursor": ""
}

try:
    print("Testing autocomplete API...")
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
