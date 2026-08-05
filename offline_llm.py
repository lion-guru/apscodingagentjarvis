"""
DevMind Offline LLM Accelerator — Local Zero-Cost Model Engine
Manages offline Ollama / vLLM local model execution when cloud APIs are unavailable.
Also supports Ollama Cloud via API key for extended model access.
"""
import os
import httpx
import json

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_CLOUD_URL = "https://api.ollama.com/v1"

class OfflineLLMAccelerator:
    def __init__(self):
        self.offline_models = ["qwen-2.5-coder-32b", "deepseek-coder", "moondream:latest", "llama3.1:8b"]
        self.cloud_api_key = os.getenv("OLLAMA_API_KEY", "")
        self.cloud_email = os.getenv("OLLAMA_EMAIL", "")

    def check_availability(self) -> dict:
        """Check if local Ollama engine is active and list available offline models."""
        result = {"online": False, "engine": "Offline Engine Standby", "available_models": [], "count": 0, "cloud_available": False}
        
        # Check local Ollama
        try:
            resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                result.update({"online": True, "engine": "Ollama Local", "available_models": models, "count": len(models)})
        except Exception:
            pass
        
        # Check Ollama Cloud
        if self.cloud_api_key:
            result["cloud_available"] = True
            result["cloud_email"] = self.cloud_email
            result["cloud_models"] = [
                "llama3.3-70b", "llama3.1-8b", "gemma2-9b", "phi3-mini",
                "qwen2.5-coder-7b", "deepseek-coder-v2", "mistral-7b"
            ]
        
        return result

    def generate_offline(self, prompt: str, model: str = "qwen-2.5-coder-32b") -> dict:
        """Generate offline completion via local model or Ollama Cloud."""
        # Try local Ollama first
        try:
            resp = httpx.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120.0
            )
            if resp.status_code == 200:
                return {"status": "ok", "response": resp.json().get("response", ""), "model": model, "source": "local"}
        except Exception:
            pass
        
        # Fallback to Ollama Cloud if API key available
        if self.cloud_api_key:
            try:
                resp = httpx.post(
                    f"{OLLAMA_CLOUD_URL}/chat/completions",
                    json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                    headers={"Authorization": f"Bearer {self.cloud_api_key}", "Content-Type": "application/json"},
                    timeout=120.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"status": "ok", "response": data["choices"][0]["message"]["content"], "model": model, "source": "ollama_cloud"}
            except Exception as e:
                return {"status": "error", "error": f"Cloud fallback failed: {e}"}
        
        return {"status": "error", "error": "No available engine (local Ollama offline, no cloud key)"}

# Global Instance
offline_accelerator = OfflineLLMAccelerator()
