"""
DevMind Offline LLM Accelerator — Local Zero-Cost Model Engine
Manages offline Ollama / vLLM local model execution when cloud APIs are unavailable.
"""
import httpx
import json

OLLAMA_HOST = "http://127.0.0.1:11434"

class OfflineLLMAccelerator:
    def __init__(self):
        self.offline_models = ["qwen-2.5-coder-32b", "deepseek-coder", "moondream:latest", "llama3.1:8b"]

    def check_availability(self) -> dict:
        """Check if local Ollama engine is active and list available offline models."""
        try:
            resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "online": True,
                    "engine": "Ollama Local",
                    "available_models": models,
                    "count": len(models)
                }
        except Exception:
            pass
        return {"online": False, "engine": "Offline Engine Standby", "available_models": [], "count": 0}

    def generate_offline(self, prompt: str, model: str = "qwen-2.5-coder-32b") -> dict:
        """Generate offline completion via local model."""
        try:
            resp = httpx.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120.0
            )
            if resp.status_code == 200:
                return {"status": "ok", "response": resp.json().get("response", ""), "model": model}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "Local Ollama engine not responding"}

# Global Instance
offline_accelerator = OfflineLLMAccelerator()
