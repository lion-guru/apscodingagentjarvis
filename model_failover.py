"""
Model Failover System for DevMind Agent
Automatically switches between free online models when quota limits are hit
"""
import os
import time
from typing import Dict, List
import httpx

# Model Failover Chain (Free Online Models First)
MODEL_FAILOVER_CHAIN = [
    {
        "name": "gemini-2.0-flash",
        "api_key": "GEMINI_API_KEY",
        "provider": "google",
        "free_tier": True,
        "quality": "high"
    },
    {
        "name": "gpt-4o-mini",
        "api_key": "OPENAI_API_KEY",
        "provider": "openai",
        "free_tier": True,
        "quality": "high"
    },
    {
        "name": "claude-3.5-sonnet",
        "api_key": "ANTHROPIC_API_KEY",
        "provider": "anthropic",
        "free_tier": True,
        "quality": "high"
    },
    {
        "name": "llama3.2:3b",
        "api_key": None,
        "provider": "ollama",
        "free_tier": True,
        "quality": "medium",
        "local": True
    },
    {
        "name": "qwen2.5:3b-instruct",
        "api_key": None,
        "provider": "ollama",
        "free_tier": True,
        "quality": "medium",
        "local": True
    }
]

class ModelFailoverManager:
    def __init__(self):
        self.current_model_index = 0
        self.failed_models = set()
        self.last_switch_time = 0
        self.switch_cooldown = 60  # seconds between switches

    def get_available_model(self) -> Dict:
        """Get next available model from failover chain"""
        for i, model_config in enumerate(MODEL_FAILOVER_CHAIN):
            if model_config["name"] not in self.failed_models:
                # Check if API key is available for non-local models
                if not model_config.get("local"):
                    api_key = os.getenv(model_config["api_key"])
                    if not api_key:
                        continue  # Skip if API key not available
                
                self.current_model_index = i
                return model_config
        
        # All models failed, return last resort (local Ollama)
        return MODEL_FAILOVER_CHAIN[-1]

    def mark_model_failed(self, model_name: str, error: str = ""):
        """Mark a model as failed and switch to next available"""
        if model_name not in self.failed_models:
            self.failed_models.add(model_name)
            print(f"[FAILOVER] Model {model_name} failed: {error}")
            print(f"[FAILOVER] Switching to next available model...")

        # Add cooldown before switching
        current_time = time.time()
        if current_time - self.last_switch_time < self.switch_cooldown:
            time.sleep(self.switch_cooldown - (current_time - self.last_switch_time))
        
        self.last_switch_time = time.time()
        next_model = self.get_available_model()
        print(f"[FAILOVER] Now using: {next_model['name']} ({next_model['provider']})")
        return next_model

    def reset_failures(self):
        """Reset failed models (call periodically to retry previously failed models)"""
        if self.failed_models:
            print(f"[FAILOVER] Resetting failed models: {self.failed_models}")
            self.failed_models.clear()
            self.current_model_index = 0

    def get_model_status(self) -> Dict:
        """Get current status of all models"""
        return {
            "current_model": MODEL_FAILOVER_CHAIN[self.current_model_index]["name"],
            "failed_models": list(self.failed_models),
            "available_models": [m["name"] for m in MODEL_FAILOVER_CHAIN if m["name"] not in self.failed_models]
        }

# Global failover manager instance
failover_manager = ModelFailoverManager()

def get_current_model() -> str:
    """Get current recommended model"""
    return failover_manager.get_available_model()["name"]

def handle_model_error(model_name: str, error: str) -> str:
    """Handle model error and return next model"""
    next_model = failover_manager.mark_model_failed(model_name, error)
    return next_model["name"]

def reset_model_failures():
    """Reset all model failures"""
    failover_manager.reset_failures()

if __name__ == "__main__":
    # Test failover system
    print("Testing Model Failover System")
    print("=" * 50)
    
    manager = ModelFailoverManager()
    
    # Get initial model
    model = manager.get_available_model()
    print(f"Initial model: {model['name']}")
    
    # Simulate failure
    next_model = manager.mark_model_failed(model['name'], "Rate limit exceeded")
    print(f"After failure: {next_model['name']}")
    
    # Get status
    status = manager.get_model_status()
    print(f"Status: {status}")
